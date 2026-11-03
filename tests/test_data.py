from __future__ import annotations

from pathlib import Path

import pytest

from plugin.chess_rules import mating_keys, parse_fen, shortest_mate
from plugin.puzzles import puzzles
from verifier.solve import line_problem

ROOT = Path(__file__).resolve().parent.parent


def test_the_verifier_has_the_same_chess_rules() -> None:
    plugin_copy = (ROOT / "src" / "plugin" / "chess_rules.py").read_bytes()
    assert (ROOT / "verifier" / "chess_rules.py").read_bytes() == plugin_copy


def test_there_are_100_puzzles_of_each_length_with_well_formed_ids() -> None:
    by_id = puzzles()
    assert len(by_id) == 200
    for n in (1, 2):
        assert sorted(p for p in by_id if p.startswith(f"m{n}-")) == [f"m{n}-{i:04d}" for i in range(1, 101)]
    assert all(puzzle["mate_in"] == int(puzzle_id[1]) for puzzle_id, puzzle in by_id.items())


@pytest.mark.parametrize("puzzle_id", sorted(puzzles()))
def test_each_puzzle_is_sound(puzzle_id: str) -> None:
    puzzle = puzzles()[puzzle_id]
    position = parse_fen(puzzle["fen"])
    n = puzzle["mate_in"]
    assert puzzle["fen"].endswith(" w - - 0 1")
    assert puzzle["keys"] == sorted(set(puzzle["keys"])) and puzzle["keys"]
    assert line_problem(position, puzzle["main_line"], puzzle["keys"][0], n) is None
    # Exact: no shorter mate, and every key found.
    assert n == 1 or shortest_mate(position, n - 1) is None
    assert mating_keys(position, n) == puzzle["keys"]
