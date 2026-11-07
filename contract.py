"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    GET_PUZZLE = "get_puzzle"
    LEGAL_MOVES = "legal_moves"
    PLAY_MOVES = "play_moves"
    SOLVE_PUZZLE = "solve_puzzle"
    SET_POSITION = "set_position"


class Task(Enum):
    GET_PUZZLE = "get-puzzle"
    SOLVE_MATE = "solve-mate"
    SET_POSITION = "set-position"


PUZZLE_ID = 'A puzzle id "m<n>-<NNNN>", where n (1 or 2) is the mate length, e.g. "m2-0042"'
SOLVE_ID = 'A bundled puzzle id such as "m2-0042", or "custom" for a position set-position gave'
FEN = (
    "A chess position in FEN, e.g. \"6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1\"; "
    "the first four fields alone are accepted, with the move counters taken as 0 1"
)
UCI = 'A move in UCI notation: from square, to square, and a promotion letter q, r, b or n if any, e.g. "e2e4", "e7e8q"'


@dataclass
class PuzzleInput(Output):
    puzzle_id: Annotated[str, PUZZLE_ID]


@dataclass
class PositionInput(Output):
    fen: Annotated[str, FEN]


@dataclass
class PuzzleOutput(Output):
    puzzle_id: Annotated[str, 'The puzzle id, as given, or "custom" for a position set from a FEN']
    fen: Annotated[str, "The starting position; the side to move is the one that mates"]
    mate_in: Annotated[
        int, "n: the side to move can force checkmate within this many of its moves, however the other side defends"
    ]
    board: Annotated[str, "The position as 8 rows, rank 8 first: uppercase White, lowercase Black, '.' empty"]


@dataclass
class LegalMovesInput(Output):
    fen: Annotated[str, FEN]


@dataclass
class LegalMovesOutput(Output):
    moves: Annotated[list[Annotated[str, UCI]], "Every legal move of the side to move, sorted"]


@dataclass
class PlayMovesInput(Output):
    fen: Annotated[str, FEN]
    lines: Annotated[
        list[list[Annotated[str, UCI]]],
        "1 to 80 lines to try, each played separately from the position: 1 to 3 moves in turn. A * before the last "
        "move stands for every legal move there, giving one result per move; a * as the last move is not played, and "
        "the result's mates lists every legal move there that gives checkmate. The lines may expand to at most 120 "
        "results",
    ]


@dataclass
class PlayedLine(Output):
    moves: Annotated[list[Annotated[str, UCI]], "The line's moves, each * before the last filled in"]
    error: Annotated[str, "Why a move could not be played, with its number; empty when every move was legal"]
    san: Annotated[list[str], "The moves played, in Standard Algebraic Notation, up to any illegal move"]
    fen: Annotated[str, "The position after the moves played, as a full six-field FEN"]
    white_to_move: Annotated[bool, "Whether White is the side to move then"]
    in_check: Annotated[bool, "Whether the side to move then is in check"]
    checkmate: Annotated[bool, "Whether the side to move then is checkmated"]
    stalemate: Annotated[bool, "Whether the side to move then is stalemated"]
    legal_replies: Annotated[int, "How many legal moves the side to move then has"]
    mates: Annotated[
        list[Annotated[str, UCI]], "When the line ends in *: every legal move of the side to move that checkmates"
    ]


@dataclass
class PlayMovesOutput(Output):
    lines: Annotated[list[PlayedLine], "One result per line, in the order given"]


@dataclass
class SolutionOutput(Output):
    puzzle_id: Annotated[str, "The puzzle's id, as given"]
    fen: Annotated[str, "The starting position"]
    mate_in: Annotated[int, "The mate length n"]
    keys: Annotated[list[Annotated[str, UCI]], "Every first move that forces mate within n, sorted"]


@dataclass
class SolveMateInput(Output):
    puzzle_id: Annotated[str, SOLVE_ID]
    fen: Annotated[str, "The starting position, exactly as get-puzzle or set-position gives it"]
    mate_in: Annotated[
        int, "n, 1 or 2, exactly as get-puzzle or set-position gives it: the side to move mates within n moves"
    ]


@dataclass
class SolveMateOutput(Output):
    puzzle_id: Annotated[str, "The puzzle's id, exactly as the task gives it"]
    key_move: Annotated[
        str,
        "The side to move's first move, which must force mate within n whatever the other side plays; a move in "
        "UCI notation: "
        'from square, to square, and a promotion letter q, r, b or n if any, e.g. "e2e4", "e7e8q"',
    ]
    main_line: Annotated[
        list[Annotated[str, UCI]],
        "One line of play from the starting position, in UCI: the key move, then alternately a defence and the "
        "attacker's reply, ending with the attacker's checkmating move; at most 2n - 1 moves",
    ]


TOOLS = {
    Tool.GET_PUZZLE: (PuzzleInput, PuzzleOutput),
    Tool.LEGAL_MOVES: (LegalMovesInput, LegalMovesOutput),
    Tool.PLAY_MOVES: (PlayMovesInput, PlayMovesOutput),
    # The reference takes the task's own input, as NanoAgent requires.
    Tool.SOLVE_PUZZLE: (SolveMateInput, SolutionOutput),
    Tool.SET_POSITION: (PositionInput, PuzzleOutput),
}
TASKS = {
    # A tool runner takes its one tool's input and output.
    Task.GET_PUZZLE: (PuzzleInput, PuzzleOutput),
    Task.SOLVE_MATE: (SolveMateInput, SolveMateOutput),
    Task.SET_POSITION: (PositionInput, PuzzleOutput),
}
