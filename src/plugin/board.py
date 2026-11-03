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
    play,
    san,
    to_fen,
    uci,
)
from plugin.chess_rules import (
    legal_moves as moves_of,
)

MAX_LINES = 80
MAX_LINE_MOVES = 3
MAX_RESULTS = 120
ANY = "*"


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
    lines = [expanded for line in given.lines for expanded in expand(start, line)]
    if len(lines) > MAX_RESULTS:
        raise ValueError(f"the lines expand to {len(lines)} results; give lines that expand to at most {MAX_RESULTS}")
    return PlayMovesOutput(lines=[play_line(start, line) for line in lines])


def expand(position, line: list[str]) -> list[list[str]]:
    """The line with each * before its last move replaced by every legal move there, in turn."""
    for index, text in enumerate(line[:-1]):
        if text != ANY:
            continue
        try:
            reached = play(position, line[:index])
        except ValueError:
            return [line]  # play_line reports the illegal move
        if not moves_of(reached):
            return [line[:index]]  # checkmate or stalemate: no move to put in its place
        return [
            expanded
            for move in moves_of(reached)
            for expanded in expand(position, [*line[:index], uci(move), *line[index + 1 :]])
        ]
    return [line]


def play_line(position, line: list[str]) -> PlayedLine:
    """The line played from the position, stopping at its first illegal move; a last * lists the mating moves."""
    played, error, mates = [], "", []
    ends_any = len(line) > 0 and line[-1] == ANY
    for number, text in enumerate(line[:-1] if ends_any else line, start=1):
        try:
            move = parse_uci(position, text)
        except ValueError as problem:
            error = f"move {number}: {problem}"
            break
        played.append(san(position, move))
        position = make_move(position, move)
    if ends_any and not error:
        mates = [uci(move) for move in moves_of(position) if is_checkmate(make_move(position, move))]
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
        mates=mates,
    )
