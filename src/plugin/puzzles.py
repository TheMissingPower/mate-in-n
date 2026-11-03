"""The bundled puzzles: get_puzzle shows one to the agent, solve_puzzle gives its keys to the verifier only."""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

from contract import PuzzleInput, PuzzleOutput, SolutionOutput, SolveMateInput
from plugin.chess_rules import board_text, parse_fen

DATA = Path(__file__).resolve().parent / "data" / "puzzles.json"
PUZZLE_ID = re.compile(r"^m[1-3]-\d{4}$")


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


def solve_puzzle(given: SolveMateInput, workspace: Path) -> SolutionOutput:
    puzzle = find(given.puzzle_id)
    return SolutionOutput(puzzle_id=puzzle["id"], fen=puzzle["fen"], mate_in=puzzle["mate_in"], keys=puzzle["keys"])
