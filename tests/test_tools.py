from __future__ import annotations

from pathlib import Path

import pytest

from contract import LegalMovesInput, PlayMovesInput, PuzzleInput, SolveMateInput
from plugin import get_puzzle, legal_moves, play_moves, solve_puzzle
from plugin.puzzles import puzzles

BACK_RANK = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"


def test_get_puzzle_gives_the_position_and_n(tmp_path: Path) -> None:
    puzzle = get_puzzle(PuzzleInput(puzzle_id="m2-0001"), tmp_path)
    assert puzzle.puzzle_id == "m2-0001" and puzzle.mate_in == 2
    assert puzzle.fen.endswith(" w - - 0 1")
    assert len(puzzle.board.splitlines()) == 9


def test_solve_puzzle_gives_the_stored_keys(tmp_path: Path) -> None:
    solution = solve_puzzle(SolveMateInput(puzzle_id="m3-0001"), tmp_path)
    assert solution.mate_in == 3 and solution.keys == puzzles()["m3-0001"]["keys"]


@pytest.mark.parametrize(("puzzle_id", "error"), [("m4-0001", ValueError), ("x", ValueError), ("m1-9999", KeyError)])
def test_refuses_unknown_or_malformed_ids(tmp_path: Path, puzzle_id: str, error: type[Exception]) -> None:
    with pytest.raises(error):
        get_puzzle(PuzzleInput(puzzle_id=puzzle_id), tmp_path)
    with pytest.raises(error):
        solve_puzzle(SolveMateInput(puzzle_id=puzzle_id), tmp_path)


def test_legal_moves(tmp_path: Path) -> None:
    output = legal_moves(LegalMovesInput(fen=BACK_RANK), tmp_path)
    assert output.white_to_move and not output.in_check
    assert "a1a8" in output.moves and output.san[output.moves.index("a1a8")] == "Ra8#"
    with pytest.raises(ValueError):
        legal_moves(LegalMovesInput(fen="not a fen"), tmp_path)


def test_play_moves(tmp_path: Path) -> None:
    output = play_moves(PlayMovesInput(fen=BACK_RANK, moves=["a1a8"]), tmp_path)
    assert output.checkmate and output.san == ["Ra8#"] and output.legal_replies == 0 and not output.white_to_move
    with pytest.raises(ValueError, match="move 2"):
        play_moves(PlayMovesInput(fen=BACK_RANK, moves=["a1a7", "a7a1"]), tmp_path)
    with pytest.raises(ValueError, match="1 to 12"):
        play_moves(PlayMovesInput(fen=BACK_RANK, moves=[]), tmp_path)
