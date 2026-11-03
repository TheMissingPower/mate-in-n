"""Checks shared by the tool verifiers. Pure functions of their arguments."""

import re

from .chess_rules import parse_fen

PUZZLE_ID = re.compile(r"^m[1-3]-\d{4}$")


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
