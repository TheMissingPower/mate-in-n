"""The chess tools the agent explores with: the legal moves of a position, and the position after some moves."""

from __future__ import annotations

from pathlib import Path

from contract import LegalMovesInput, LegalMovesOutput, PlayMovesInput, PlayMovesOutput
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

MAX_MOVES = 12


def legal_moves(given: LegalMovesInput, workspace: Path) -> LegalMovesOutput:
    position = parse_fen(given.fen)
    moves = moves_of(position)
    return LegalMovesOutput(
        fen=to_fen(position),
        white_to_move=position.white,
        moves=[uci(move) for move in moves],
        san=[san(position, move) for move in moves],
        in_check=in_check(position),
        checkmate=is_checkmate(position),
        stalemate=is_stalemate(position),
    )


def play_moves(given: PlayMovesInput, workspace: Path) -> PlayMovesOutput:
    if not 1 <= len(given.moves) <= MAX_MOVES:
        raise ValueError(f"give 1 to {MAX_MOVES} moves")
    position = parse_fen(given.fen)
    played = []
    for number, text in enumerate(given.moves, start=1):
        try:
            move = parse_uci(position, text)
        except ValueError as error:
            raise ValueError(f"move {number}: {error}") from None
        played.append(san(position, move))
        position = make_move(position, move)
    return PlayMovesOutput(
        fen=to_fen(position),
        san=played,
        white_to_move=position.white,
        in_check=in_check(position),
        checkmate=is_checkmate(position),
        stalemate=is_stalemate(position),
        legal_replies=len(moves_of(position)),
    )
