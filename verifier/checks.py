"""Checks shared by the tool verifiers. Pure functions of their arguments."""

import re

from .chess_rules import parse_fen, to_fen

PUZZLE_ID = re.compile(r"^m[12]-\d{4}$")


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def puzzle_id_problem(puzzle_id):
    if not PUZZLE_ID.match(puzzle_id):
        return f'{puzzle_id!r} is not a puzzle id such as "m2-0042"'
    return None


def position_or_problem(fen):
    """(the position, None) for a legal FEN, or (None, why not)."""
    try:
        return parse_fen(fen), None
    except ValueError as error:
        return None, f"not a legal position: {error}"


def task_input_problem(value):
    """Why solve-mate's input is not a puzzle id with a legal start and a matching n, or None."""
    problem = puzzle_id_problem(value.puzzle_id)
    if problem:
        return problem
    return puzzle_position_problem(value.fen, value.mate_in, value.puzzle_id)


def same_start_problem(value, fen, mate_in):
    """Why the task input's fen and mate_in are not the given puzzle's, or None."""
    position, problem = position_or_problem(value.fen)
    if problem:
        return problem
    if to_fen(position) != fen or value.mate_in != mate_in:
        return f"the fen and mate_in are not those of {value.puzzle_id}"
    return None


def puzzle_position_problem(fen, mate_in, puzzle_id):
    """Why a puzzle's start does not fit the plugin's puzzles, or None: White to move, no castling or en passant."""
    position, problem = position_or_problem(fen)
    if problem:
        return problem
    if not position.white or position.castling or position.ep is not None:
        return "a puzzle starts with White to move, with no castling rights and no en passant square"
    if mate_in != int(puzzle_id[1]):
        return f"mate_in {mate_in} does not match the id {puzzle_id}"
    return None
