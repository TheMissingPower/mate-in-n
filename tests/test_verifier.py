from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import (
    LegalMovesInput,
    LegalMovesOutput,
    PlayMovesInput,
    PlayMovesOutput,
    PositionInput,
    PuzzleInput,
    PuzzleOutput,
    SolutionOutput,
    SolveMateInput,
    SolveMateOutput,
)
from plugin import get_puzzle, legal_moves, play_moves, set_position, solve_puzzle
from plugin.chess_rules import legal_moves as moves_of
from plugin.chess_rules import main_line, mating_keys, parse_fen, play, uci
from plugin.puzzles import puzzles

HERE = Path(".")
TWO_ROOKS = "6k1/5ppp/8/8/8/8/8/RR4K1 w - - 0 1"  # mate in 1, by a1a8 or b1b8
PROMOTION = "k7/2P5/1K6/8/8/8/8/8 w - - 0 1"  # mate in 1, by c7c8q or c7c8r
BLACK_MATE_IN_2 = "6B1/2nn2p1/4r3/6Kp/1P4Pr/qkP3b1/N6N/1b6 b - - 0 1"  # m2-0001 with colours swapped: d7f6


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def built(value, cls):
    return build_output(plain_output(value), cls)


def task_input(puzzle_id: str) -> SolveMateInput:
    puzzle = stored(puzzle_id)
    return SolveMateInput(puzzle_id=puzzle_id, fen=puzzle["fen"], mate_in=puzzle["mate_in"])


def reference(puzzle_id: str) -> SolutionOutput:
    return built(solve_puzzle(task_input(puzzle_id), HERE), SolutionOutput)


def made_up(puzzle_id: str, fen: str, keys: list[str]) -> SolutionOutput:
    return built(SolutionOutput(puzzle_id=puzzle_id, fen=fen, mate_in=int(puzzle_id[1]), keys=keys), SolutionOutput)


def judge(
    puzzle_id: str,
    key: str,
    line: list[str],
    ref: SolutionOutput | None,
    answer_id: str | None = None,
    fen: str | None = None,
):
    # The task input carries the puzzle's start: a bundled puzzle's own, or the made-up reference's.
    start = fen or (stored(puzzle_id)["fen"] if puzzle_id in puzzles() else ref.fen)
    arguments = build_output({"puzzle_id": puzzle_id, "fen": start, "mate_in": int(puzzle_id[1])}, SolveMateInput)
    output = build_output({"puzzle_id": answer_id or puzzle_id, "key_move": key, "main_line": line}, SolveMateOutput)
    first = verifier.verify_task("solve-mate", arguments, output, ref, str(HERE))
    # The sandbox runs the verifier twice; both verdicts must match.
    assert verifier.verify_task("solve-mate", arguments, output, ref, str(HERE)) == first
    return first


def stored(puzzle_id: str) -> dict:
    return puzzles()[puzzle_id]


# Correct answers.


@pytest.mark.parametrize("puzzle_id", ["m1-0001", "m2-0001", "m1-0100", "m2-0100"])
def test_accepts_the_stored_solution(puzzle_id: str) -> None:
    puzzle = stored(puzzle_id)
    verdict = judge(puzzle_id, puzzle["keys"][0], puzzle["main_line"], reference(puzzle_id))
    assert verdict["valid"] is True and verdict["score"] == 1.0
    # The page draws the main line from the start the verdict gives.
    assert verdict["details"]["fen"] == puzzle["fen"]


def test_accepts_any_key_that_forces_mate() -> None:
    ref = made_up("m1-9001", TWO_ROOKS, ["a1a8", "b1b8"])
    assert judge("m1-9001", "b1b8", ["b1b8"], ref)["valid"] is True
    assert judge("m1-9001", "a1a8", ["a1a8"], ref)["valid"] is True


def test_accepts_a_line_with_another_black_defence() -> None:
    puzzle = stored("m2-0001")
    position = parse_fen(puzzle["fen"])
    after_key = play(position, [puzzle["keys"][0]])
    for reply in (uci(move) for move in moves_of(after_key)):
        mates = mating_keys(play(after_key, [reply]), 1)
        if reply != puzzle["main_line"][1] and mates:
            line = [puzzle["keys"][0], reply, mates[0]]
            assert judge("m2-0001", puzzle["keys"][0], line, reference("m2-0001"))["valid"] is True
            return
    pytest.skip("m2-0001 has only one black defence")


def test_accepts_a_promotion_key() -> None:
    ref = made_up("m1-9002", PROMOTION, ["c7c8q", "c7c8r"])
    assert judge("m1-9002", "c7c8r", ["c7c8r"], ref)["valid"] is True


# Wrong answers.


def test_rejects_a_legal_key_that_does_not_force_mate() -> None:
    puzzle = stored("m2-0001")
    position = parse_fen(puzzle["fen"])
    wrong = next(uci(move) for move in moves_of(position) if uci(move) not in puzzle["keys"])
    verdict = judge("m2-0001", wrong, [wrong], reference("m2-0001"))
    assert verdict["valid"] is False and verdict["score"] == 0.0 and "does not force mate" in verdict["message"]
    assert verdict["details"]["fen"] == puzzle["fen"]


def test_rejects_a_key_that_mates_only_after_a_bad_defence() -> None:
    # Every first move of a mate in 2 is refuted somehow, even one after which some defence loses at once.
    for puzzle_id in sorted(p for p in puzzles() if p.startswith("m2-")):
        puzzle = stored(puzzle_id)
        position = parse_fen(puzzle["fen"])
        for move in (uci(m) for m in moves_of(position)):
            if move in puzzle["keys"]:
                continue
            after = play(position, [move])
            for reply in (uci(m) for m in moves_of(after)):
                mates = mating_keys(play(after, [reply]), 1)
                if mates:
                    verdict = judge(puzzle_id, move, [move, reply, mates[0]], reference(puzzle_id))
                    assert verdict["valid"] is False and verdict["score"] == 0.0
                    return
    pytest.fail("no tempting wrong key found")


def test_gives_half_credit_for_the_key_with_a_line_that_does_not_mate() -> None:
    puzzle = stored("m2-0001")
    key, reply = puzzle["main_line"][0], puzzle["main_line"][1]
    after = play(parse_fen(puzzle["fen"]), [key, reply])
    quiet = next(uci(move) for move in moves_of(after) if uci(move) not in mating_keys(after, 1))
    verdict = judge("m2-0001", key, [key, reply, quiet], reference("m2-0001"))
    assert verdict["valid"] is False and verdict["score"] == 0.5 and "checkmated" in verdict["message"]


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ([], "missing"),
        (["b1b8"], "not the key"),
        (["a1a8", "g8h8", "a8a7"], "more than"),
        (["a1a8", "Kh8"], "more than"),
        (["a1a7"], "not the key"),
    ],
)
def test_gives_half_credit_for_a_broken_line(line: list[str], message: str) -> None:
    ref = made_up("m1-9001", TWO_ROOKS, ["a1a8", "b1b8"])
    verdict = judge("m1-9001", "a1a8", line, ref)
    assert verdict["valid"] is False and verdict["score"] == 0.5 and message in verdict["message"]


def test_gives_half_credit_for_an_illegal_or_malformed_line_move() -> None:
    puzzle = stored("m2-0001")
    key = puzzle["keys"][0]
    for bad, message in (("a1a1", "not legal"), ("Kh8", "not a UCI move")):
        verdict = judge("m2-0001", key, [key, bad, puzzle["main_line"][2]], reference("m2-0001"))
        assert verdict["score"] == 0.5 and message in verdict["message"]


# Missing and malformed answers.


@pytest.mark.parametrize("key", ["", "Ra8#", "Ra8", "a1-a8", "A1A8", " a1a8", "a1a8 ", "e9e10", "a1a8x", "0-0"])
def test_rejects_a_malformed_key(key: str) -> None:
    ref = made_up("m1-9001", TWO_ROOKS, ["a1a8", "b1b8"])
    verdict = judge("m1-9001", key, ["a1a8"], ref)
    assert verdict["valid"] is False and verdict["score"] == 0.0 and "malformed" in verdict["message"]


def test_rejects_an_illegal_key_and_a_promotion_without_its_letter() -> None:
    ref = made_up("m1-9002", PROMOTION, ["c7c8q", "c7c8r"])
    for key in ("c7c8", "c7c6", "b6a7"):
        verdict = judge("m1-9002", key, [key], ref)
        assert verdict["valid"] is False and verdict["score"] == 0.0 and "not legal" in verdict["message"]


def test_rejects_an_answer_for_another_puzzle() -> None:
    puzzle = stored("m1-0001")
    verdict = judge("m1-0001", puzzle["keys"][0], puzzle["main_line"], reference("m1-0001"), answer_id="m1-0002")
    assert verdict["valid"] is False and verdict["score"] == 0.0


# A broken reference never yields a pass.


def test_rejects_a_task_input_whose_start_is_not_the_puzzles() -> None:
    puzzle = stored("m2-0001")
    key, line = puzzle["keys"][0], puzzle["main_line"]
    verdict = judge("m2-0001", key, line, reference("m2-0001"), fen=stored("m2-0002")["fen"])
    assert verdict["valid"] is False and verdict["score"] == 0.0 and "task input is broken" in verdict["message"]


def test_rejects_without_a_sound_reference() -> None:
    puzzle = stored("m1-0001")
    key, line = puzzle["keys"][0], puzzle["main_line"]
    assert judge("m1-0001", key, line, None)["valid"] is False
    assert judge("m1-0001", key, line, reference("m1-0002"))["valid"] is False
    bad_fen = built(replace(reference("m1-0001"), fen="8/8/8/8/8/8/8/8 w - - 0 1"), SolutionOutput)
    assert "reference is broken" in judge("m1-0001", key, line, bad_fen)["message"]


def test_reports_an_integrity_failure_when_proof_and_reference_disagree() -> None:
    # The right key missing from the reference, or a wrong key listed in it.
    missing = made_up("m1-9001", TWO_ROOKS, ["b1b8"])
    verdict = judge("m1-9001", "a1a8", ["a1a8"], missing)
    assert verdict["valid"] is False and verdict["score"] == 0.0 and "integrity" in verdict["message"]
    planted = made_up("m1-9001", TWO_ROOKS, ["a1a7", "a1a8", "b1b8"])
    verdict = judge("m1-9001", "a1a7", ["a1a7"], planted)
    assert verdict["valid"] is False and verdict["score"] == 0.0 and "integrity" in verdict["message"]


# The tool checks.


def test_tool_inputs() -> None:
    assert verifier.verify_input("get_puzzle", build_output({"puzzle_id": "m2-0042"}, PuzzleInput))["valid"]
    assert verifier.verify_input("solve_puzzle", built(task_input("m2-0042"), SolveMateInput))["valid"]
    for bad in ("m3-0001", "m4-0001", "m2-42", "M2-0042", ""):
        assert not verifier.verify_input("get_puzzle", build_output({"puzzle_id": bad}, PuzzleInput))["valid"]
        given = build_output({"puzzle_id": bad, "fen": TWO_ROOKS, "mate_in": 1}, SolveMateInput)
        assert not verifier.verify_input("solve_puzzle", given)["valid"]
    for change in ({"mate_in": 1}, {"fen": "nonsense"}, {"fen": TWO_ROOKS.replace(" w ", " b ")}):
        given = built(replace(task_input("m2-0042"), **change), SolveMateInput)
        assert not verifier.verify_input("solve_puzzle", given)["valid"], change
    assert not verifier.verify_input("legal_moves", build_output({"fen": "nonsense"}, LegalMovesInput))["valid"]
    for lines in ([], [["a1a8"]] * 81, [[]], [["a1a2"] * 4], [["Ra8"]], [["*", "*", "*"]] * 10):
        given = build_output({"fen": TWO_ROOKS, "lines": lines}, PlayMovesInput)
        assert not verifier.verify_input("play_moves", given)["valid"], lines
    given = build_output(
        {"fen": TWO_ROOKS, "lines": [["a1a8"], ["a1a7", "g8h8", "a7a8"], ["a1a7", "*", "*"]]}, PlayMovesInput
    )
    assert verifier.verify_input("play_moves", given)["valid"]


def test_get_puzzle_output() -> None:
    given = build_output({"puzzle_id": "m2-0007"}, PuzzleInput)
    made = built(get_puzzle(given, HERE), PuzzleOutput)
    assert verifier.verify_output("get_puzzle", given, made, ".")["valid"]
    # The get-puzzle task runs the tool and is judged the same way.
    assert verifier.verify_task("get-puzzle", given, made, None, ".")["valid"]
    for change in ({"mate_in": 1}, {"puzzle_id": "m2-0008"}, {"board": "."}, {"fen": made.fen.replace(" w ", " b ")}):
        tampered = built(replace(made, **change), PuzzleOutput)
        assert not verifier.verify_output("get_puzzle", given, tampered, ".")["valid"], change
        assert not verifier.verify_task("get-puzzle", given, tampered, None, ".")["valid"], change


def test_solve_puzzle_output() -> None:
    given = built(task_input("m2-0003"), SolveMateInput)
    made = built(solve_puzzle(given, HERE), SolutionOutput)
    assert verifier.verify_output("solve_puzzle", given, made, ".")["valid"]
    position = parse_fen(made.fen)
    wrong = next(uci(move) for move in moves_of(position) if uci(move) not in made.keys)
    for keys in ([], sorted(made.keys + [wrong]), made.keys + made.keys):
        tampered = built(replace(made, keys=keys), SolutionOutput)
        assert not verifier.verify_output("solve_puzzle", given, tampered, ".")["valid"], keys
    assert not verifier.verify_output("solve_puzzle", given, built(replace(made, mate_in=1), SolutionOutput), ".")[
        "valid"
    ]
    other = built(replace(given, fen=stored("m2-0004")["fen"]), SolveMateInput)
    assert not verifier.verify_output("solve_puzzle", other, made, ".")["valid"]


def test_legal_moves_output() -> None:
    given = build_output({"fen": stored("m2-0001")["fen"]}, LegalMovesInput)
    made = built(legal_moves(given, HERE), LegalMovesOutput)
    assert verifier.verify_output("legal_moves", given, made, ".")["valid"]
    for change in ({"moves": made.moves[1:]}, {"moves": list(reversed(made.moves))}, {"moves": made.moves + ["a1a1"]}):
        tampered = built(replace(made, **change), LegalMovesOutput)
        assert not verifier.verify_output("legal_moves", given, tampered, ".")["valid"]


def test_play_moves_output() -> None:
    given = build_output({"fen": TWO_ROOKS, "lines": [["a1a8"], ["a1a7", "g8h8"], ["a1a7", "a7a1"]]}, PlayMovesInput)
    made = built(play_moves(given, HERE), PlayMovesOutput)
    assert made.lines[0].checkmate and made.lines[2].error
    assert verifier.verify_output("play_moves", given, made, ".")["valid"]
    for change in ({"checkmate": False}, {"legal_replies": 1}, {"fen": TWO_ROOKS}, {"error": "move 1: no"}):
        tampered = built(replace(made, lines=[replace(made.lines[0], **change), *made.lines[1:]]), PlayMovesOutput)
        assert not verifier.verify_output("play_moves", given, tampered, ".")["valid"], change
    for lines in (made.lines[:2], [*made.lines, made.lines[0]], list(reversed(made.lines))):
        tampered = built(replace(made, lines=lines), PlayMovesOutput)
        assert not verifier.verify_output("play_moves", given, tampered, ".")["valid"]


def test_play_moves_output_with_stars() -> None:
    given = build_output({"fen": TWO_ROOKS, "lines": [["*"], ["a1a7", "*", "*"], ["a1a8", "*", "*"]]}, PlayMovesInput)
    made = built(play_moves(given, HERE), PlayMovesOutput)
    assert made.lines[0].mates == ["a1a8", "b1b8"] and len(made.lines) > 3
    assert verifier.verify_output("play_moves", given, made, ".")["valid"]
    for change in ({"mates": []}, {"mates": ["a1a8"]}, {"moves": ["*", "*"]}):
        tampered = built(replace(made, lines=[replace(made.lines[0], **change), *made.lines[1:]]), PlayMovesOutput)
        assert not verifier.verify_output("play_moves", given, tampered, ".")["valid"], change
    tampered = built(replace(made, lines=made.lines[:-1]), PlayMovesOutput)
    assert not verifier.verify_output("play_moves", given, tampered, ".")["valid"]


# Custom positions, set from any FEN.


def custom_judge(fen: str, mate_in: int, key: str, line: list[str]):
    arguments = build_output({"puzzle_id": "custom", "fen": fen, "mate_in": mate_in}, SolveMateInput)
    ref = built(solve_puzzle(arguments, HERE), SolutionOutput)
    output = build_output({"puzzle_id": "custom", "key_move": key, "main_line": line}, SolveMateOutput)
    return verifier.verify_task("solve-mate", arguments, output, ref, str(HERE))


def test_solves_a_custom_position_with_black_to_move() -> None:
    position = parse_fen(BLACK_MATE_IN_2)
    line = main_line(position, "d7f6", 2)
    verdict = custom_judge(BLACK_MATE_IN_2, 2, "d7f6", line)
    assert verdict["valid"] and verdict["score"] == 1.0, verdict
    # A key that does not force mate scores nothing, and a line that stops short of mate gets half.
    wrong = next(uci(move) for move in moves_of(position) if uci(move) != "d7f6")
    assert custom_judge(BLACK_MATE_IN_2, 2, wrong, [wrong])["score"] == 0.0
    assert custom_judge(BLACK_MATE_IN_2, 2, "d7f6", line[:2])["score"] == 0.5


def test_set_position_output() -> None:
    given = build_output({"fen": BLACK_MATE_IN_2}, PositionInput)
    made = built(set_position(given, HERE), PuzzleOutput)
    assert verifier.verify_output("set_position", given, made, ".")["valid"]
    assert verifier.verify_task("set-position", given, made, None, ".")["valid"]
    for change in ({"mate_in": 1}, {"puzzle_id": "m2-0001"}, {"board": "."}, {"fen": TWO_ROOKS}):
        tampered = built(replace(made, **change), PuzzleOutput)
        assert not verifier.verify_output("set_position", given, tampered, ".")["valid"], change
    assert not verifier.verify_input("set_position", build_output({"fen": "nonsense"}, PositionInput))["valid"]


def test_custom_solve_inputs() -> None:
    def valid(fen, mate_in):
        given = build_output({"puzzle_id": "custom", "fen": fen, "mate_in": mate_in}, SolveMateInput)
        return verifier.verify_input("solve_puzzle", given)["valid"]

    assert valid(BLACK_MATE_IN_2, 2) and valid(TWO_ROOKS, 1)
    assert not valid(BLACK_MATE_IN_2, 1) and not valid(TWO_ROOKS, 2)
    assert not valid("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 2)
