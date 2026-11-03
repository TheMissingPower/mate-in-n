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
    san,
    to_fen,
    uci,
)

MAX_MOVES = 12


def verify_legal_moves_input(value):
    _, problem = position_or_problem(value.fen)
    if problem:
        return result(False, problem)
    return result(True, "input is valid")


def verify_play_moves_input(value):
    _, problem = position_or_problem(value.fen)
    if problem:
        return result(False, problem)
    if not 1 <= len(value.moves) <= MAX_MOVES:
        return result(False, f"give 1 to {MAX_MOVES} moves")
    malformed = [move for move in value.moves if not UCI_PATTERN.match(move)]
    if malformed:
        return result(False, f"not UCI moves: {', '.join(malformed)}")
    return result(True, "input is valid")


def verify_legal_moves_output(input_value, output_value, workspace):
    position, problem = position_or_problem(input_value.fen)
    if problem:
        return result(False, problem)
    moves = legal_moves(position)
    expected = {
        "fen": to_fen(position),
        "white_to_move": position.white,
        "moves": [uci(move) for move in moves],
        "san": [san(position, move) for move in moves],
        "in_check": in_check(position),
        "checkmate": is_checkmate(position),
        "stalemate": is_stalemate(position),
    }
    given = {
        "fen": output_value.fen,
        "white_to_move": output_value.white_to_move,
        "moves": output_value.moves,
        "san": output_value.san,
        "in_check": output_value.in_check,
        "checkmate": output_value.checkmate,
        "stalemate": output_value.stalemate,
    }
    wrong = sorted(name for name in expected if expected[name] != given[name])
    if wrong:
        return result(False, f"wrong {', '.join(wrong)}", wrong=wrong)
    return result(True, "legal moves are right", count=len(moves))


def verify_play_moves_output(input_value, output_value, workspace):
    position, problem = position_or_problem(input_value.fen)
    if problem:
        return result(False, problem)
    sans = []
    try:
        for text in input_value.moves:
            move = parse_uci(position, text)
            sans.append(san(position, move))
            position = make_move(position, move)
    except ValueError as error:
        return result(False, f"the moves cannot be played: {error}")
    expected = {
        "fen": to_fen(position),
        "san": sans,
        "white_to_move": position.white,
        "in_check": in_check(position),
        "checkmate": is_checkmate(position),
        "stalemate": is_stalemate(position),
        "legal_replies": len(legal_moves(position)),
    }
    given = {
        "fen": output_value.fen,
        "san": output_value.san,
        "white_to_move": output_value.white_to_move,
        "in_check": output_value.in_check,
        "checkmate": output_value.checkmate,
        "stalemate": output_value.stalemate,
        "legal_replies": output_value.legal_replies,
    }
    wrong = sorted(name for name in expected if expected[name] != given[name])
    if wrong:
        return result(False, f"wrong {', '.join(wrong)}", wrong=wrong)
    return result(True, "the moves are played right", fen=output_value.fen)
