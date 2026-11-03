"""The deterministic verifier: each tool's checks live in a module of their own, on contract instances."""

from contract import Task, Tool

from . import board, puzzle, solve

# tool -> (verify_input(value), verify_output(input_value, output_value, workspace))
TOOLS = {
    Tool.GET_PUZZLE: (puzzle.verify_input, puzzle.verify_puzzle),
    Tool.LEGAL_MOVES: (board.verify_legal_moves_input, board.verify_legal_moves_output),
    Tool.PLAY_MOVES: (board.verify_play_moves_input, board.verify_play_moves_output),
    Tool.SOLVE_PUZZLE: (puzzle.verify_input, puzzle.verify_solution),
}
# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.SOLVE_MATE: solve.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)][0](value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)][1](input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
