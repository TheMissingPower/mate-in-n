"""The puzzles: get_puzzle looks a bundled one up by id, set_position makes one from any FEN, and solve_puzzle gives
its keys to the verifier only."""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

from contract import PositionInput, PuzzleInput, PuzzleOutput, SolutionOutput, SolveMateInput
from plugin.chess_rules import board_text, has_legal_move, mating_keys, parse_fen, shortest_mate, to_fen

DATA = Path(__file__).resolve().parent / "data" / "puzzles.json"
PUZZLE_ID = re.compile(r"^m[12]-\d{4}$")
# The id of a position set from a FEN, whose keys are searched for when asked, not stored.
CUSTOM = "custom"
# The longest mate a position may take: the agent's lines are at most 3 moves, 2n - 1 for n = 2.
MAX_MATE = 2


@cache
def puzzles() -> dict[str, dict]:
    """Every bundled puzzle by id, as tools_dev/build_puzzles.py wrote it."""
    return {puzzle["id"]: puzzle for puzzle in json.loads(DATA.read_text(encoding="utf-8"))["puzzles"]}


def find(puzzle_id: str) -> dict:
    if not PUZZLE_ID.match(puzzle_id):
        raise ValueError(f'{puzzle_id!r} is not a puzzle id such as "m2-0042"')
    if puzzle_id not in puzzles():
        raise KeyError(f"there is no puzzle {puzzle_id}")
    return puzzles()[puzzle_id]


def get_puzzle(given: PuzzleInput, workspace: Path) -> PuzzleOutput:
    puzzle = find(given.puzzle_id)
    return PuzzleOutput(
        puzzle_id=puzzle["id"],
        fen=puzzle["fen"],
        mate_in=puzzle["mate_in"],
        board=board_text(parse_fen(puzzle["fen"])),
    )


def mate_length(position) -> int:
    """The fewest moves in which the side to move forces mate. Raises ValueError if it cannot within MAX_MATE."""
    if not has_legal_move(position):
        raise ValueError("the game is already over in this position")
    n = shortest_mate(position, MAX_MATE)
    if n is None:
        side = "White" if position.white else "Black"
        raise ValueError(f"{side}, to move, cannot force checkmate within {MAX_MATE} moves")
    return n


def set_position(given: PositionInput, workspace: Path) -> PuzzleOutput:
    position = parse_fen(given.fen)
    return PuzzleOutput(
        puzzle_id=CUSTOM, fen=to_fen(position), mate_in=mate_length(position), board=board_text(position)
    )


def solve_puzzle(given: SolveMateInput, workspace: Path) -> SolutionOutput:
    if given.puzzle_id == CUSTOM:
        position = parse_fen(given.fen)
        n = mate_length(position)
        if given.mate_in != n:
            raise ValueError(f"the shortest forced mate is in {n}, not {given.mate_in}: copy mate_in from set-position")
        return SolutionOutput(puzzle_id=CUSTOM, fen=to_fen(position), mate_in=n, keys=mating_keys(position, n))
    puzzle = find(given.puzzle_id)
    if to_fen(parse_fen(given.fen)) != puzzle["fen"] or given.mate_in != puzzle["mate_in"]:
        raise ValueError(f"the fen and mate_in are not those of {puzzle['id']}: copy them from get-puzzle")
    return SolutionOutput(puzzle_id=puzzle["id"], fen=puzzle["fen"], mate_in=puzzle["mate_in"], keys=puzzle["keys"])
