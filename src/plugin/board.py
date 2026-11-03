"""The chess tools the agent explores with: the legal moves of a position, and the position after some moves."""

from __future__ import annotations

from pathlib import Path

from contract import LegalMovesInput, LegalMovesOutput, PlayedLine, PlayMovesInput, PlayMovesOutput
from plugin.chess_rules import (
    in_check,
    is_checkmate,
    is_stalemate,
    make_move,
    parse_fen,
    parse_uci,
    san,
    to_fen,
    uci,
)
from plugin.chess_rules import (
    legal_moves as moves_of,
)

MAX_LINES = 30
MAX_LINE_MOVES = 3


def legal_moves(given: LegalMovesInput, workspace: Path) -> LegalMovesOutput:
    # Only the moves: no SAN, whose + and # would show the agent which moves check or mate.
    return LegalMovesOutput(moves=[uci(move) for move in moves_of(parse_fen(given.fen))])


def play_moves(given: PlayMovesInput, workspace: Path) -> PlayMovesOutput:
    if not 1 <= len(given.lines) <= MAX_LINES:
        raise ValueError(f"give 1 to {MAX_LINES} lines")
    for number, line in enumerate(given.lines, start=1):
        if not 1 <= len(line) <= MAX_LINE_MOVES:
            raise ValueError(f"line {number}: give 1 to {MAX_LINE_MOVES} moves")
    start = parse_fen(given.fen)
    return PlayMovesOutput(lines=[play_line(start, line) for line in given.lines])


def play_line(position, line: list[str]) -> PlayedLine:
    """The line played from the position, stopping at its first illegal move."""
    played, error = [], ""
    for number, text in enumerate(line, start=1):
        try:
            move = parse_uci(position, text)
        except ValueError as problem:
            error = f"move {number}: {problem}"
            break
        played.append(san(position, move))
        position = make_move(position, move)
    return PlayedLine(
        moves=list(line),
        error=error,
        san=played,
        fen=to_fen(position),
        white_to_move=position.white,
        in_check=in_check(position),
        checkmate=is_checkmate(position),
        stalemate=is_stalemate(position),
        legal_replies=len(moves_of(position)),
    )
