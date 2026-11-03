"""get_puzzle (and the get-puzzle task) looks up a puzzle; solve_puzzle, solve-mate's reference, gives its keys."""

from .checks import puzzle_id_problem, puzzle_position_problem, result, same_start_problem, task_input_problem
from .chess_rules import board_text, forces_mate, has_legal_move, parse_fen, parse_uci, shortest_mate


def verify_input(value):
    problem = puzzle_id_problem(value.puzzle_id)
    if problem:
        return result(False, problem)
    return result(True, "input is valid")


def verify_solve_input(value):
    problem = task_input_problem(value)
    if problem:
        return result(False, problem)
    return result(True, "input is valid")


def verify_lookup(arguments, output, reference, workspace):
    return verify_puzzle(arguments, output, workspace)


def verify_puzzle(input_value, output_value, workspace):
    if output_value.puzzle_id != input_value.puzzle_id:
        return result(False, "the puzzle is not the one asked for")
    problem = puzzle_position_problem(output_value.fen, output_value.mate_in, output_value.puzzle_id)
    if problem:
        return result(False, problem)
    position = parse_fen(output_value.fen)
    if not has_legal_move(position):
        return result(False, "the puzzle is already over")
    if output_value.board != board_text(position):
        return result(False, "the board diagram does not show the position")
    return result(True, "puzzle is valid", puzzle_id=output_value.puzzle_id, mate_in=output_value.mate_in)


def verify_solution(input_value, output_value, workspace):
    if output_value.puzzle_id != input_value.puzzle_id:
        return result(False, "the solution is not for the puzzle asked for")
    problem = puzzle_position_problem(output_value.fen, output_value.mate_in, output_value.puzzle_id)
    if problem:
        return result(False, problem)
    problem = same_start_problem(input_value, output_value.fen, output_value.mate_in)
    if problem:
        return result(False, problem)
    keys, n = output_value.keys, output_value.mate_in
    if not keys or keys != sorted(set(keys)):
        return result(False, "the keys must be a non-empty, sorted list without repeats")
    position = parse_fen(output_value.fen)
    for key in keys:
        try:
            move = parse_uci(position, key)
        except ValueError as error:
            return result(False, f"key {key}: {error}")
        if not forces_mate(position, move, n):
            return result(False, f"key {key} does not force mate in {n}")
    if n > 1 and shortest_mate(position, n - 1) is not None:
        return result(False, f"White can mate in fewer than {n} moves")
    return result(True, "every key forces mate", keys=keys, mate_in=n)
