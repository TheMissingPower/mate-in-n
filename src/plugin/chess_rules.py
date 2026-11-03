"""Chess rules in pure standard-library Python: FEN, legal moves, UCI and SAN, check and mate, forced-mate search.

This exact file is kept twice, as src/plugin/chess_rules.py and verifier/chess_rules.py, because the verifier may
import only the standard library and its own package. tests/test_data.py fails if the two copies differ.

Squares are 0..63 with a1 = 0, b1 = 1, ..., h8 = 63. A move is a tuple (from_square, to_square, promotion), where
promotion is "" or one of "q", "r", "b", "n".
"""

import re

FILES = "abcdefgh"
PIECES = "PNBRQKpnbrqk"
PROMOTIONS = "qrbn"
UCI_PATTERN = re.compile(r"^[a-h][1-8][a-h][1-8][qrbn]?$")
_CASTLING_PATTERN = re.compile(r"^(-|K?Q?k?q?)$")
_EMPTY = "."


def square_name(square):
    return FILES[square % 8] + str(square // 8 + 1)


def _steps(offsets):
    table = []
    for square in range(64):
        file, rank = square % 8, square // 8
        table.append(
            [(rank + dr) * 8 + file + df for df, dr in offsets if 0 <= file + df < 8 and 0 <= rank + dr < 8]
        )
    return table


def _rays(directions):
    table = []
    for square in range(64):
        file, rank = square % 8, square // 8
        rays = []
        for df, dr in directions:
            ray, f, r = [], file + df, rank + dr
            while 0 <= f < 8 and 0 <= r < 8:
                ray.append(r * 8 + f)
                f, r = f + df, r + dr
            rays.append(ray)
        table.append(rays)
    return table


KNIGHT_STEPS = _steps([(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)])
KING_STEPS = _steps([(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)])
ROOK_RAYS = _rays([(1, 0), (-1, 0), (0, 1), (0, -1)])
BISHOP_RAYS = _rays([(1, 1), (1, -1), (-1, 1), (-1, -1)])
# The squares from which a pawn of that colour attacks the given square.
WHITE_PAWN_ATTACKERS = _steps([(-1, -1), (1, -1)])
BLACK_PAWN_ATTACKERS = _steps([(-1, 1), (1, 1)])


class Position:
    """A legal chess position. Build one with parse_fen; make_move returns a new one."""

    __slots__ = ("board", "castling", "ep", "fullmove", "halfmove", "white")

    def __init__(self, board, white, castling, ep, halfmove, fullmove):
        self.board = board
        self.white = white
        self.castling = castling
        self.ep = ep
        self.halfmove = halfmove
        self.fullmove = fullmove


def parse_fen(fen):
    """The position a FEN names. Raises ValueError for a malformed FEN or an impossible position."""
    fields = fen.strip().split()
    if len(fields) == 4:
        fields += ["0", "1"]
    if len(fields) != 6:
        raise ValueError("a FEN has 6 space-separated fields")
    placement, turn, castling, ep, halfmove, fullmove = fields
    ranks = placement.split("/")
    if len(ranks) != 8:
        raise ValueError("the piece placement must have 8 ranks")
    board = [_EMPTY] * 64
    for index, text in enumerate(ranks):
        rank, file = 7 - index, 0
        for char in text:
            if char in "12345678":
                file += int(char)
            elif char in PIECES:
                if file > 7:
                    raise ValueError(f"rank {rank + 1} has more than 8 squares")
                board[rank * 8 + file] = char
                file += 1
            else:
                raise ValueError(f"unknown piece {char!r}")
        if file != 8:
            raise ValueError(f"rank {rank + 1} does not have 8 squares")
    if turn not in ("w", "b"):
        raise ValueError("the side to move must be w or b")
    if not _CASTLING_PATTERN.match(castling):
        raise ValueError("castling rights must be - or a subset of KQkq in that order")
    if ep == "-":
        ep_square = None
    elif re.match(r"^[a-h][36]$", ep) and ep[1] == ("6" if turn == "w" else "3"):
        ep_square = (int(ep[1]) - 1) * 8 + FILES.index(ep[0])
    else:
        raise ValueError("the en passant square must be - or on the rank behind the pawn that just moved")
    if not (halfmove.isdigit() and fullmove.isdigit() and int(fullmove) >= 1):
        raise ValueError("the move counters must be whole numbers, the fullmove at least 1")
    if board.count("K") != 1 or board.count("k") != 1:
        raise ValueError("each side must have exactly one king")
    if any(board[s] in "Pp" for s in list(range(8)) + list(range(56, 64))):
        raise ValueError("a pawn cannot stand on the first or last rank")
    if ep_square is not None:
        pawn, behind = ("p", ep_square - 8) if turn == "w" else ("P", ep_square + 8)
        if board[behind] != pawn or board[ep_square] != _EMPTY:
            raise ValueError("the en passant square must be behind a pawn that just moved two squares")
    rights = "" if castling == "-" else castling
    for right, king, rook in (("K", 4, 7), ("Q", 4, 0), ("k", 60, 63), ("q", 60, 56)):
        piece = "K" if right.isupper() else "k"
        if right in rights and (board[king] != piece or board[rook] != ("R" if right.isupper() else "r")):
            raise ValueError(f"castling right {right} needs its king and rook on their starting squares")
    position = Position(board, turn == "w", rights, ep_square, int(halfmove), int(fullmove))
    if _king_attacked(board, not position.white):
        raise ValueError("the side not to move is in check")
    return position


def to_fen(position):
    rows = []
    for rank in range(7, -1, -1):
        row, empty = "", 0
        for file in range(8):
            piece = position.board[rank * 8 + file]
            if piece == _EMPTY:
                empty += 1
                continue
            if empty:
                row += str(empty)
                empty = 0
            row += piece
        rows.append(row + (str(empty) if empty else ""))
    ep = "-" if position.ep is None else square_name(position.ep)
    turn = "w" if position.white else "b"
    return f"{'/'.join(rows)} {turn} {position.castling or '-'} {ep} {position.halfmove} {position.fullmove}"


def board_text(position):
    """An 8-line diagram, rank 8 first, with '.' for empty squares and file letters underneath."""
    lines = []
    for rank in range(7, -1, -1):
        lines.append(f"{rank + 1} " + " ".join(position.board[rank * 8 : rank * 8 + 8]))
    lines.append("  " + " ".join(FILES))
    return "\n".join(lines)


def attacked(board, square, by_white):
    """Whether any piece of the given colour attacks the square."""
    pawn, knight, king = ("P", "N", "K") if by_white else ("p", "n", "k")
    straight, diagonal = ("RQ", "BQ") if by_white else ("rq", "bq")
    for source in (WHITE_PAWN_ATTACKERS if by_white else BLACK_PAWN_ATTACKERS)[square]:
        if board[source] == pawn:
            return True
    for source in KNIGHT_STEPS[square]:
        if board[source] == knight:
            return True
    for source in KING_STEPS[square]:
        if board[source] == king:
            return True
    for sliders, rays in ((straight, ROOK_RAYS), (diagonal, BISHOP_RAYS)):
        for ray in rays[square]:
            for source in ray:
                piece = board[source]
                if piece != _EMPTY:
                    if piece in sliders:
                        return True
                    break
    return False


def _king_attacked(board, white):
    """Whether the king of the given colour is attacked by the other side."""
    return attacked(board, board.index("K" if white else "k"), not white)


def in_check(position):
    return _king_attacked(position.board, position.white)


def _own(piece, white):
    return piece != _EMPTY and piece.isupper() == white


def _pseudo_moves(position):
    board, white = position.board, position.white
    moves = []
    for square in range(64):
        piece = board[square]
        if not _own(piece, white):
            continue
        kind = piece.upper()
        if kind == "P":
            forward = 8 if white else -8
            start_rank, last_rank = (1, 7) if white else (6, 0)
            promotions = PROMOTIONS if (square + forward) // 8 == last_rank else ("",)
            target = square + forward
            if board[target] == _EMPTY:
                moves += [(square, target, p) for p in promotions]
                if square // 8 == start_rank and board[target + forward] == _EMPTY:
                    moves.append((square, target + forward, ""))
            for target in (BLACK_PAWN_ATTACKERS if white else WHITE_PAWN_ATTACKERS)[square]:
                victim = board[target]
                if (victim != _EMPTY and not _own(victim, white)) or target == position.ep:
                    moves += [(square, target, p) for p in promotions]
        elif kind in "NK":
            for target in (KNIGHT_STEPS if kind == "N" else KING_STEPS)[square]:
                if not _own(board[target], white):
                    moves.append((square, target, ""))
        else:
            rays = (ROOK_RAYS[square] if kind in "RQ" else []) + (BISHOP_RAYS[square] if kind in "BQ" else [])
            for ray in rays:
                for target in ray:
                    victim = board[target]
                    if victim == _EMPTY:
                        moves.append((square, target, ""))
                        continue
                    if not _own(victim, white):
                        moves.append((square, target, ""))
                    break
    moves += _castling_moves(position)
    return moves


def _castling_moves(position):
    board, white, rights = position.board, position.white, position.castling
    king, (short, long) = (4, "KQ") if white else (60, "kq")
    moves = []
    short_free = short in rights and board[king + 1] == board[king + 2] == _EMPTY
    if short_free and not any(attacked(board, s, not white) for s in (king, king + 1, king + 2)):
        moves.append((king, king + 2, ""))
    long_free = long in rights and board[king - 1] == board[king - 2] == board[king - 3] == _EMPTY
    if long_free and not any(attacked(board, s, not white) for s in (king, king - 1, king - 2)):
        moves.append((king, king - 2, ""))
    return moves


# A right is lost when anything moves from or to its king's or rook's starting square.
_RIGHTS_LOST = {4: "KQ", 7: "K", 0: "Q", 60: "kq", 63: "k", 56: "q"}


def _apply(position, move):
    """The position after a pseudo-legal move; it may leave the mover's king in check."""
    source, target, promotion = move
    board = position.board[:]
    piece = board[source]
    capture = board[target] != _EMPTY
    board[source] = _EMPTY
    board[target] = (promotion.upper() if position.white else promotion) if promotion else piece
    kind = piece.upper()
    if kind == "P" and target == position.ep:
        board[target - 8 if position.white else target + 8] = _EMPTY
        capture = True
    if kind == "K" and abs(target - source) == 2:
        rook_from, rook_to = (source + 3, source + 1) if target > source else (source - 4, source - 1)
        board[rook_to], board[rook_from] = board[rook_from], _EMPTY
    rights = position.castling
    for square in (source, target):
        for right in _RIGHTS_LOST.get(square, ""):
            rights = rights.replace(right, "")
    ep = (source + target) // 2 if kind == "P" and abs(target - source) == 16 else None
    halfmove = 0 if kind == "P" or capture else position.halfmove + 1
    fullmove = position.fullmove + (0 if position.white else 1)
    return Position(board, not position.white, rights, ep, halfmove, fullmove)


def _legal_children(position):
    """Every legal move with the position it leads to, in a fixed order."""
    children = []
    for move in _pseudo_moves(position):
        child = _apply(position, move)
        if not _king_attacked(child.board, position.white):
            children.append((move, child))
    return children


def legal_moves(position):
    """Every legal move, sorted by its UCI text."""
    return sorted((move for move, _ in _legal_children(position)), key=uci)


def has_legal_move(position):
    for move in _pseudo_moves(position):
        if not _king_attacked(_apply(position, move).board, position.white):
            return True
    return False


def is_checkmate(position):
    return in_check(position) and not has_legal_move(position)


def is_stalemate(position):
    return not in_check(position) and not has_legal_move(position)


def uci(move):
    source, target, promotion = move
    return square_name(source) + square_name(target) + promotion


def parse_uci(position, text):
    """The legal move a UCI string names. Raises ValueError for malformed text or an illegal move."""
    if not isinstance(text, str) or not UCI_PATTERN.match(text):
        raise ValueError(f"{text!r} is not a UCI move such as e2e4 or e7e8q")
    for move, _ in _legal_children(position):
        if uci(move) == text:
            return move
    raise ValueError(f"{text} is not a legal move in this position")


def make_move(position, move):
    """The position after a legal move."""
    return _apply(position, move)


def play(position, texts):
    """The position after a sequence of UCI moves, each of which must be legal in turn."""
    for text in texts:
        position = make_move(position, parse_uci(position, text))
    return position


def san(position, move):
    """The move in Standard Algebraic Notation, with + for check and # for mate."""
    source, target, promotion = move
    piece = position.board[source].upper()
    capture = position.board[target] != _EMPTY or (piece == "P" and target == position.ep)
    if piece == "K" and abs(target - source) == 2:
        text = "O-O" if target > source else "O-O-O"
    elif piece == "P":
        text = (FILES[source % 8] + "x" if capture else "") + square_name(target)
        text += "=" + promotion.upper() if promotion else ""
    else:
        rivals = [
            m[0]
            for m, _ in _legal_children(position)
            if m[1] == target and m[0] != source and position.board[m[0]].upper() == piece
        ]
        hint = ""
        if rivals:
            if all(r % 8 != source % 8 for r in rivals):
                hint = FILES[source % 8]
            elif all(r // 8 != source // 8 for r in rivals):
                hint = str(source // 8 + 1)
            else:
                hint = square_name(source)
        text = piece + hint + ("x" if capture else "") + square_name(target)
    child = _apply(position, move)
    if in_check(child):
        text += "#" if not has_legal_move(child) else "+"
    return text


def perft(position, depth):
    """The number of leaf positions after exactly depth plies: the standard move-generator test."""
    if depth == 0:
        return 1
    children = _legal_children(position)
    if depth == 1:
        return len(children)
    return sum(perft(child, depth - 1) for _, child in children)


# Forced mate. "The attacker" is the side to move in the starting position; it must mate within n of its moves
# whatever the defender plays. Stalemate is a failure for the attacker.


def _wins(position, n):
    """Whether the side to move can force mate within n of its own moves."""
    checks, quiet = [], []
    for _, child in _legal_children(position):
        (checks if in_check(child) else quiet).append(child)
    candidates = checks if n == 1 else checks + quiet
    return any(_lost(child, n) for child in candidates)


def _lost(position, n):
    """Whether the side to move (the defender) is mated now, or within n - 1 more attacker moves whatever it does."""
    replies = _legal_children(position)
    if not replies:
        return in_check(position)
    if n == 1:
        return False
    return all(_wins(child, n - 1) for _, child in replies)


def forces_mate(position, move, n):
    """Whether the legal move forces mate within n moves of the side playing it, counting this move."""
    return _lost(make_move(position, move), n)


def mating_keys(position, n):
    """The UCI text of every first move that forces mate within n moves, sorted."""
    return sorted(uci(move) for move, child in _legal_children(position) if _lost(child, n))


def shortest_mate(position, limit):
    """The fewest moves in which the side to move forces mate, or None if it cannot within limit."""
    for n in range(1, limit + 1):
        if _wins(position, n):
            return n
    return None


def main_line(position, key, n):
    """One line from the forcing key to mate: the attacker mates fastest, the defender resists longest.

    Raises ValueError if the key does not force mate within n.
    """
    move = parse_uci(position, key)
    if not forces_mate(position, move, n):
        raise ValueError(f"{key} does not force mate in {n}")
    line = [key]
    position = make_move(position, move)
    remaining = n
    while True:
        replies = sorted(_legal_children(position), key=lambda pair: uci(pair[0]))
        if not replies:
            return line
        # The defender's reply after which the attacker needs the most moves.
        reply, after, need = None, None, 0
        for move, child in replies:
            fewest = next(k for k in range(1, remaining) if _wins(child, k))
            if fewest > need:
                reply, after, need = move, child, fewest
        line.append(uci(reply))
        # The attacker's first move that mates within need.
        for move, child in sorted(_legal_children(after), key=lambda pair: uci(pair[0])):
            if _lost(child, need):
                line.append(uci(move))
                position, remaining = child, need
                break
