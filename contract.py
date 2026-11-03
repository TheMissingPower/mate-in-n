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


class Task(Enum):
    SOLVE_MATE = "solve-mate"


PUZZLE_ID = 'A puzzle id "m<n>-<NNNN>", where n (1, 2 or 3) is the mate length, e.g. "m2-0042"'
FEN = (
    "A chess position in FEN, e.g. \"6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1\"; "
    "the first four fields alone are accepted, with the move counters taken as 0 1"
)
UCI = 'A move in UCI notation: from square, to square, and a promotion letter q, r, b or n if any, e.g. "e2e4", "e7e8q"'


@dataclass
class PuzzleInput(Output):
    puzzle_id: Annotated[str, PUZZLE_ID]


@dataclass
class PuzzleOutput(Output):
    puzzle_id: Annotated[str, "The puzzle's id, as given"]
    fen: Annotated[str, "The starting position: White to move, no castling, no en passant"]
    mate_in: Annotated[int, "n: White can force checkmate within this many White moves, however Black defends"]
    board: Annotated[str, "The position as 8 rows, rank 8 first: uppercase White, lowercase Black, '.' empty"]


@dataclass
class LegalMovesInput(Output):
    fen: Annotated[str, FEN]


@dataclass
class LegalMovesOutput(Output):
    fen: Annotated[str, "The position, as a full six-field FEN"]
    white_to_move: Annotated[bool, "Whether White is the side to move"]
    moves: Annotated[list[Annotated[str, UCI]], "Every legal move of the side to move, sorted"]
    san: Annotated[list[str], "The same moves in Standard Algebraic Notation, in the same order"]
    in_check: Annotated[bool, "Whether the side to move is in check"]
    checkmate: Annotated[bool, "Whether the side to move is checkmated"]
    stalemate: Annotated[bool, "Whether the side to move is stalemated"]


@dataclass
class PlayMovesInput(Output):
    fen: Annotated[str, FEN]
    moves: Annotated[list[Annotated[str, UCI]], "1 to 12 moves to play in turn from the position, each legal when played"]


@dataclass
class PlayMovesOutput(Output):
    fen: Annotated[str, "The position after the moves, as a full six-field FEN"]
    san: Annotated[list[str], "The moves played, in Standard Algebraic Notation"]
    white_to_move: Annotated[bool, "Whether White is the side to move now"]
    in_check: Annotated[bool, "Whether the side to move now is in check"]
    checkmate: Annotated[bool, "Whether the side to move now is checkmated"]
    stalemate: Annotated[bool, "Whether the side to move now is stalemated"]
    legal_replies: Annotated[int, "How many legal moves the side to move now has"]


@dataclass
class SolutionOutput(Output):
    puzzle_id: Annotated[str, "The puzzle's id, as given"]
    fen: Annotated[str, "The starting position"]
    mate_in: Annotated[int, "The mate length n"]
    keys: Annotated[list[Annotated[str, UCI]], "Every first move that forces mate within n, sorted"]


@dataclass
class SolveMateInput(Output):
    puzzle_id: Annotated[str, PUZZLE_ID]


@dataclass
class SolveMateOutput(Output):
    puzzle_id: Annotated[str, "The puzzle's id, exactly as the task gives it"]
    key_move: Annotated[
        str,
        "White's first move, which must force mate within n whatever Black plays; a move in UCI notation: "
        'from square, to square, and a promotion letter q, r, b or n if any, e.g. "e2e4", "e7e8q"',
    ]
    main_line: Annotated[
        list[Annotated[str, UCI]],
        "One line of play from the starting position, in UCI: the key move, then alternately a Black defence and "
        "White's reply, ending with White's checkmating move; at most 2n - 1 moves",
    ]


TOOLS = {
    Tool.GET_PUZZLE: (PuzzleInput, PuzzleOutput),
    Tool.LEGAL_MOVES: (LegalMovesInput, LegalMovesOutput),
    Tool.PLAY_MOVES: (PlayMovesInput, PlayMovesOutput),
    # The reference takes the task's own input, as NanoAgent requires.
    Tool.SOLVE_PUZZLE: (SolveMateInput, SolutionOutput),
}
TASKS = {Task.SOLVE_MATE: (SolveMateInput, SolveMateOutput)}
