from __future__ import annotations

from pathlib import Path

import pytest

from contract import LegalMovesInput, PlayMovesInput, PuzzleInput, SolveMateInput
from plugin import get_puzzle, legal_moves, play_moves, solve_puzzle
from plugin.puzzles import puzzles

BACK_RANK = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"


def task_input(puzzle_id: str) -> SolveMateInput:
    puzzle = puzzles()[puzzle_id]
    return SolveMateInput(puzzle_id=puzzle_id, fen=puzzle["fen"], mate_in=puzzle["mate_in"])


def test_get_puzzle_gives_the_position_and_n(tmp_path: Path) -> None:
    puzzle = get_puzzle(PuzzleInput(puzzle_id="m2-0001"), tmp_path)
    assert puzzle.puzzle_id == "m2-0001" and puzzle.mate_in == 2
    assert puzzle.fen.endswith(" w - - 0 1")
    assert len(puzzle.board.splitlines()) == 9


def test_solve_puzzle_gives_the_stored_keys(tmp_path: Path) -> None:
    solution = solve_puzzle(task_input("m2-0001"), tmp_path)
    assert solution.mate_in == 2 and solution.keys == puzzles()["m2-0001"]["keys"]


def test_solve_puzzle_accepts_a_four_field_fen(tmp_path: Path) -> None:
    given = task_input("m1-0001")
    short = SolveMateInput(puzzle_id=given.puzzle_id, fen=given.fen.removesuffix(" 0 1"), mate_in=1)
    assert solve_puzzle(short, tmp_path).keys == puzzles()["m1-0001"]["keys"]


def test_solve_puzzle_refuses_a_start_that_is_not_the_puzzles(tmp_path: Path) -> None:
    given = task_input("m2-0001")
    for wrong in (
        SolveMateInput(puzzle_id="m2-0001", fen=puzzles()["m2-0002"]["fen"], mate_in=2),
        SolveMateInput(puzzle_id="m2-0001", fen=given.fen, mate_in=1),
    ):
        with pytest.raises(ValueError, match="not those of m2-0001"):
            solve_puzzle(wrong, tmp_path)


@pytest.mark.parametrize(
    ("puzzle_id", "error"), [("m3-0001", ValueError), ("m4-0001", ValueError), ("x", ValueError), ("m1-9999", KeyError)]
)
def test_refuses_unknown_or_malformed_ids(tmp_path: Path, puzzle_id: str, error: type[Exception]) -> None:
    with pytest.raises(error):
        get_puzzle(PuzzleInput(puzzle_id=puzzle_id), tmp_path)
    with pytest.raises(error):
        solve_puzzle(SolveMateInput(puzzle_id=puzzle_id, fen=BACK_RANK, mate_in=1), tmp_path)


def test_legal_moves_gives_only_the_moves(tmp_path: Path) -> None:
    output = legal_moves(LegalMovesInput(fen=BACK_RANK), tmp_path)
    assert "a1a8" in output.moves and output.moves == sorted(output.moves)
    # Nothing marks a move as checking or mating.
    assert [field for field in vars(output)] == ["moves"]
    with pytest.raises(ValueError):
        legal_moves(LegalMovesInput(fen="not a fen"), tmp_path)


def test_play_moves_plays_each_line_separately(tmp_path: Path) -> None:
    output = play_moves(PlayMovesInput(fen=BACK_RANK, lines=[["a1a8"], ["a1a7", "g8h8"], ["a1a7", "a7a1"]]), tmp_path)
    mate, quiet, illegal = output.lines
    assert mate.checkmate and mate.san == ["Ra8#"] and mate.legal_replies == 0 and not mate.white_to_move
    assert mate.error == "" and mate.moves == ["a1a8"]
    assert not quiet.checkmate and quiet.white_to_move and quiet.san == ["Ra7", "Kh8"]
    # A line stops at its illegal move; the others still play.
    assert illegal.error.startswith("move 2:") and illegal.san == ["Ra7"] and not illegal.white_to_move


@pytest.mark.parametrize(
    ("lines", "message"),
    [([], "1 to 30 lines"), ([["a1a8"]] * 31, "1 to 30 lines"), ([[]], "line 1"), ([["a1a2"] * 4], "line 1")],
)
def test_play_moves_refuses_too_many_or_too_few(tmp_path: Path, lines: list[list[str]], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        play_moves(PlayMovesInput(fen=BACK_RANK, lines=lines), tmp_path)
