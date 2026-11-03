"""The solve-mate task: does the submitted key force mate within n, and does the main line end in checkmate?"""

from .checks import puzzle_position_problem, result
from .chess_rules import UCI_PATTERN, forces_mate, is_checkmate, make_move, parse_fen, parse_uci

# The share of the score for a key that forces mate when the main line does not show a mate.
KEY_ONLY_SCORE = 0.5


def verify_task(arguments, output, reference, workspace):
    if reference is None:
        return result(False, "the task has no reference solution to check against", score=0.0)
    if reference.puzzle_id != arguments.puzzle_id:
        return result(False, "the reference is for another puzzle", score=0.0)
    problem = puzzle_position_problem(reference.fen, reference.mate_in, reference.puzzle_id)
    if problem:
        return result(False, f"the reference is broken: {problem}", score=0.0)
    if output.puzzle_id != arguments.puzzle_id:
        return result(False, f"the answer is for {output.puzzle_id!r}, not {arguments.puzzle_id}", score=0.0)
    position, n, key = parse_fen(reference.fen), reference.mate_in, output.key_move
    if not UCI_PATTERN.match(key):
        return result(False, f"the key move {key!r} is malformed: give it in UCI, such as e2e4 or e7e8q", score=0.0)
    try:
        move = parse_uci(position, key)
    except ValueError:
        return result(False, f"the key move {key} is not legal in the puzzle", score=0.0, key=key)
    proved, listed = forces_mate(position, move, n), key in reference.keys
    if proved != listed:
        return result(False, f"integrity failure: the proof and the reference disagree on {key}", score=0.0, key=key)
    if not proved:
        return result(False, f"{key} does not force mate in {n}", score=0.0, key=key, keys=reference.keys)
    problem = line_problem(position, output.main_line, key, n)
    if problem:
        return result(False, f"{key} forces mate in {n}, but {problem}", score=KEY_ONLY_SCORE, key=key)
    return result(True, f"{key} forces mate in {n}, and the main line ends in checkmate", key=key, mate_in=n)


def line_problem(position, line, key, n):
    """Why the line is not a legal line from the key to a checkmate within n White moves, or None."""
    if not line:
        return "the main line is missing"
    if line[0] != key:
        return f"the main line starts with {line[0]!r}, not the key move"
    if len(line) > 2 * n - 1:
        return f"the main line has {len(line)} moves, more than the {2 * n - 1} a mate in {n} takes"
    for number, text in enumerate(line, start=1):
        if not UCI_PATTERN.match(text):
            return f"main line move {number}, {text!r}, is not a UCI move"
        try:
            position = make_move(position, parse_uci(position, text))
        except ValueError:
            return f"main line move {number}, {text}, is not legal there"
    if position.white or not is_checkmate(position):
        return "the main line does not end with Black checkmated"
    return None
