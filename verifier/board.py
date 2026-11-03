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

MAX_LINES = 30
MAX_LINE_MOVES = 3


def verify_legal_moves_input(value):
    _, problem = position_or_problem(value.fen)
    if problem:
        return result(False, problem)
    return result(True, "input is valid")


def verify_play_moves_input(value):
    _, problem = position_or_problem(value.fen)
    if problem:
        return result(False, problem)
    if not 1 <= len(value.lines) <= MAX_LINES:
        return result(False, f"give 1 to {MAX_LINES} lines")
    for number, line in enumerate(value.lines, start=1):
        if not 1 <= len(line) <= MAX_LINE_MOVES:
            return result(False, f"line {number}: give 1 to {MAX_LINE_MOVES} moves")
        malformed = [move for move in line if not UCI_PATTERN.match(move)]
        if malformed:
            return result(False, f"line {number}: not UCI moves: {', '.join(malformed)}")
    return result(True, "input is valid")


def verify_legal_moves_output(input_value, output_value, workspace):
    position, problem = position_or_problem(input_value.fen)
    if problem:
        return result(False, problem)
    moves = [uci(move) for move in legal_moves(position)]
    if output_value.moves != moves:
        return result(False, "wrong moves", wrong=["moves"])
    return result(True, "legal moves are right", count=len(moves))


def expected_line(position, line):
    """What play_moves gives for the line: played up to its first illegal move."""
    sans, error = [], ""
    for number, text in enumerate(line, start=1):
        try:
            move = parse_uci(position, text)
        except ValueError as problem:
            error = f"move {number}: {problem}"
            break
        sans.append(san(position, move))
        position = make_move(position, move)
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
    }


def verify_play_moves_output(input_value, output_value, workspace):
    position, problem = position_or_problem(input_value.fen)
    if problem:
        return result(False, problem)
    if len(output_value.lines) != len(input_value.lines):
        return result(False, f"{len(output_value.lines)} results for {len(input_value.lines)} lines")
    for number, (line, played) in enumerate(zip(input_value.lines, output_value.lines), start=1):
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
        }
        wrong = sorted(name for name in expected if expected[name] != given[name])
        if wrong:
            return result(False, f"line {number}: wrong {', '.join(wrong)}", line=number, wrong=wrong)
    return result(True, "the lines are played right", lines=len(output_value.lines))
