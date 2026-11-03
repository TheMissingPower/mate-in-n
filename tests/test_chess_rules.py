from __future__ import annotations

import pytest

from plugin.chess_rules import (
    in_check,
    is_checkmate,
    is_stalemate,
    legal_moves,
    main_line,
    mating_keys,
    parse_fen,
    parse_uci,
    perft,
    play,
    san,
    shortest_mate,
    to_fen,
    uci,
)

# Standard perft positions (chessprogramming.org/Perft_Results) and their leaf counts by depth.
PERFT = [
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", [20, 400, 8902]),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", [48, 2039]),
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", [14, 191, 2812]),
    ("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", [6, 264]),
    ("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", [44, 1486]),
    ("r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", [46, 2079]),
]


@pytest.mark.parametrize(("fen", "counts"), PERFT)
def test_perft_matches_the_reference_counts(fen: str, counts: list[int]) -> None:
    position = parse_fen(fen)
    assert [perft(position, depth) for depth in range(1, len(counts) + 1)] == counts


def test_fen_round_trips() -> None:
    for fen, _ in PERFT:
        assert to_fen(parse_fen(fen)) == fen
    assert to_fen(parse_fen("8/8/8/8/8/8/8/K6k w - -")) == "8/8/8/8/8/8/8/K6k w - - 0 1"


@pytest.mark.parametrize(
    "fen",
    [
        "",
        "8/8/8/8/8/8/8/K6k w - - 0",  # five fields
        "8/8/8/8/8/8/K6k w - - 0 1",  # seven ranks
        "9/8/8/8/8/8/8/K6k w - - 0 1",  # a rank of nine squares
        "8/8/8/8/8/8/8/K5k w - - 0 1",  # a rank of seven squares
        "8/8/8/8/8/8/8/K6x w - - 0 1",  # an unknown piece
        "8/8/8/8/8/8/8/K6k x - - 0 1",  # no side to move
        "8/8/8/8/8/8/8/K6k w KQ - 0 1",  # castling without king and rooks at home
        "8/8/8/8/8/8/8/K6k w - e3 0 1",  # en passant on the wrong rank
        "8/8/8/8/8/8/8/K6k w - e6 0 1",  # en passant with no pawn that just moved
        "8/8/8/8/8/8/8/K6k w - - x 1",  # a bad counter
        "8/8/8/8/8/8/8/K7 w - - 0 1",  # no black king
        "8/8/8/8/8/8/8/KK5k w - - 0 1",  # two white kings
        "P7/8/8/8/8/8/8/K6k w - - 0 1",  # a pawn on the last rank
        "k7/8/8/8/8/8/8/R5K1 w - - 0 1",  # Black, not to move, is in check
    ],
)
def test_refuses_malformed_or_impossible_fens(fen: str) -> None:
    with pytest.raises(ValueError):
        parse_fen(fen)


def test_en_passant_captures_the_pawn_and_respects_pins() -> None:
    position = parse_fen("8/8/8/3pP3/8/8/8/4K2k w - d6 0 1")
    after = play(position, ["e5d6"])
    assert to_fen(after).split()[0] == "8/8/3P4/8/8/8/8/4K2k"
    pinned = parse_fen("8/8/8/K2pP2r/8/8/8/7k w - d6 0 1")
    assert "e5d6" not in [uci(move) for move in legal_moves(pinned)]


def test_a_pinned_piece_cannot_move() -> None:
    position = parse_fen("4r2k/8/8/8/8/8/4B3/4K3 w - - 0 1")
    assert not any(uci(move).startswith("e2") for move in legal_moves(position))


def test_castling_is_refused_through_an_attacked_square() -> None:
    free = parse_fen("4k3/8/8/8/8/8/8/4K2R w K - 0 1")
    assert san(free, parse_uci(free, "e1g1")) == "O-O"
    attacked = parse_fen("4k3/8/8/8/8/8/5r2/4K2R w K - 0 1")
    assert "e1g1" not in [uci(move) for move in legal_moves(attacked)]


def test_promotions_need_their_letter() -> None:
    position = parse_fen("k7/2P5/1K6/8/8/8/8/8 w - - 0 1")
    moves = [uci(move) for move in legal_moves(position)]
    assert {"c7c8q", "c7c8r", "c7c8b", "c7c8n"} <= set(moves)
    with pytest.raises(ValueError, match="not a legal move"):
        parse_uci(position, "c7c8")
    with pytest.raises(ValueError, match="not a UCI move"):
        parse_uci(position, "Qc8")
    assert san(position, parse_uci(position, "c7c8q")) == "c8=Q#"
    assert mating_keys(position, 1) == ["c7c8q", "c7c8r"]


def test_check_mate_and_stalemate() -> None:
    mate = play(parse_fen("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"), ["a1a8"])
    assert in_check(mate) and is_checkmate(mate) and not is_stalemate(mate)
    stalemate = parse_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert is_stalemate(stalemate) and not is_checkmate(stalemate)


def test_san_disambiguates() -> None:
    position = parse_fen("4k3/8/8/8/8/8/4K3/R6R w - - 0 1")
    assert san(position, parse_uci(position, "a1d1")) == "Rad1"
    assert san(position, parse_uci(position, "h1d1")) == "Rhd1"


def test_mate_search() -> None:
    back_rank = parse_fen("6k1/5ppp/8/8/8/8/8/RR4K1 w - - 0 1")
    assert shortest_mate(back_rank, 3) == 1
    assert mating_keys(back_rank, 1) == ["a1a8", "b1b8"]
    assert main_line(back_rank, "a1a8", 1) == ["a1a8"]
    # Stalemating Black is not a mate.
    assert shortest_mate(parse_fen("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1"), 1) == 1
    stalemating = parse_fen("7k/8/6K1/8/8/8/8/5Q2 w - - 0 1")
    assert is_stalemate(play(stalemating, ["f1f7"]))
    assert "f1f7" not in mating_keys(stalemating, 2)
    with pytest.raises(ValueError, match="does not force mate"):
        main_line(back_rank, "g1f1", 1)
