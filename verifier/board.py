"""legal_moves and play_moves, recomputed with the verifier's own copy of the rules."""

from .checks import position_or_problem, result
from .chess_rules import (
    UCI_PATTERN,
    in_check,
    is_checkmate,
    is_stalemate,
    legal_moves,
    make_move,
    parse_uci,
    play,
    san,
    to_fen,
    uci,
)

MAX_LINES = 80
MAX_LINE_MOVES = 3
MAX_RESULTS = 120
ANY = "*"


def verify_legal_moves_input(value):
    _, problem = position_or_problem(value.fen)
    if problem:
        return result(False, problem)
    return result(True, "input is valid")


def verify_play_moves_input(value):
    position, problem = position_or_problem(value.fen)
    if problem:
        return result(False, problem)
    if not 1 <= len(value.lines) <= MAX_LINES:
        return result(False, f"give 1 to {MAX_LINES} lines")
    for number, line in enumerate(value.lines, start=1):
        if not 1 <= len(line) <= MAX_LINE_MOVES:
            return result(False, f"line {number}: give 1 to {MAX_LINE_MOVES} moves")
        malformed = [move for move in line if move != ANY and not UCI_PATTERN.match(move)]
        if malformed:
            return result(False, f"line {number}: not UCI moves: {', '.join(malformed)}")
    count = len(expanded_lines(position, value.lines))
    if count > MAX_RESULTS:
        return result(False, f"the lines expand to {count} results; give lines that expand to at most {MAX_RESULTS}")
    return result(True, "input is valid")


def verify_legal_moves_output(input_value, output_value, workspace):
    position, problem = position_or_problem(input_value.fen)
    if problem:
        return result(False, problem)
    moves = [uci(move) for move in legal_moves(position)]
    if output_value.moves != moves:
        return result(False, "wrong moves", wrong=["moves"])
    return result(True, "legal moves are right", count=len(moves))


def expand(position, line):
    """The line with each * before its last move replaced by every legal move there, in turn."""
    for index, text in enumerate(line[:-1]):
        if text != ANY:
            continue
        try:
            reached = play(position, line[:index])
        except ValueError:
            return [line]
        if not legal_moves(reached):
            return [line[:index]]
        return [
            expanded
            for move in legal_moves(reached)
            for expanded in expand(position, [*line[:index], uci(move), *line[index + 1 :]])
        ]
    return [line]


def expanded_lines(position, lines):
    return [expanded for line in lines for expanded in expand(position, line)]


def expected_line(position, line):
    """What play_moves gives for the line: played up to its first illegal move; a last * lists the mating moves."""
    sans, error, mates = [], "", []
    ends_any = len(line) > 0 and line[-1] == ANY
    for number, text in enumerate(line[:-1] if ends_any else line, start=1):
        try:
            move = parse_uci(position, text)
        except ValueError as problem:
            error = f"move {number}: {problem}"
            break
        sans.append(san(position, move))
        position = make_move(position, move)
    if ends_any and not error:
        mates = [uci(move) for move in legal_moves(position) if is_checkmate(make_move(position, move))]
    return {
        "moves": list(line),
        "error": error,
        "san": sans,
        "fen": to_fen(position),
        "white_to_move": position.white,
        "in_check": in_check(position),
        "checkmate": is_checkmate(position),
        "stalemate": is_stalemate(position),
        "legal_replies": len(legal_moves(position)),
        "mates": mates,
    }


def verify_play_moves_output(input_value, output_value, workspace):
    position, problem = position_or_problem(input_value.fen)
    if problem:
        return result(False, problem)
    lines = expanded_lines(position, input_value.lines)
    if len(output_value.lines) != len(lines):
        return result(False, f"{len(output_value.lines)} results for {len(lines)} lines")
    for number, (line, played) in enumerate(zip(lines, output_value.lines), start=1):
        expected = expected_line(position, line)
        given = {
            "moves": played.moves,
            "error": played.error,
            "san": played.san,
            "fen": played.fen,
            "white_to_move": played.white_to_move,
            "in_check": played.in_check,
            "checkmate": played.checkmate,
            "stalemate": played.stalemate,
            "legal_replies": played.legal_replies,
            "mates": played.mates,
        }
        wrong = sorted(name for name in expected if expected[name] != given[name])
        if wrong:
            return result(False, f"line {number}: wrong {', '.join(wrong)}", line=number, wrong=wrong)
    return result(True, "the lines are played right", lines=len(output_value.lines))
