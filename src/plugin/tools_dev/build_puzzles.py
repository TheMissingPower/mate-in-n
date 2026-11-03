"""Builds src/plugin/data/puzzles.json from the 432k-chess-puzzles collection of yacpdb.org problems.

Run once from the plugin folder. Its output is committed, so the plugin never needs the network:

    uv run python -m plugin.tools_dev.build_puzzles [--source FILE] [--workers N]

The collection gives only each problem's piece placement, with no side to move and no solution. This script:
- reads the file at a pinned commit and checks its SHA-256;
- drops fairy-piece and impossible positions;
- sets White to move with no castling and no en passant, the usual direct-mate convention;
- shuffles with a fixed seed;
- finds each position's shortest forced mate with the plugin's own engine, keeping exact mates in 1 and 2.

Candidates whose search takes longer than SEARCH_LIMIT seconds are skipped. The limit depends on the machine,
so a rebuild elsewhere can choose different puzzles; tests/test_data.py checks the committed file itself.
"""

import argparse
import hashlib
import json
import multiprocessing
import queue
import random
import time
import urllib.request
from pathlib import Path

from plugin.chess_rules import forces_mate, main_line, mating_keys, parse_fen, parse_uci, shortest_mate

COMMIT = "dcb2b72ce945940c8489f5e2625a89c35b44060b"
SOURCE_URL = f"https://raw.githubusercontent.com/rebeccaloran/432k-chess-puzzles/{COMMIT}/432k-chess-puzzles-sorted.fen"
SOURCE_SHA256 = "b1b20af96146a4eb1a87e6f353a12ff4e3181edac8d89198b129a78812e297b6"
SEED = 480
PER_LENGTH = 100
LENGTHS = (1, 2)
SEARCH_LIMIT = 10.0
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "puzzles.json"


def read_source(source):
    data = Path(source).read_bytes() if source else urllib.request.urlopen(SOURCE_URL, timeout=120).read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SOURCE_SHA256:
        raise SystemExit(f"source SHA-256 is {digest}, expected {SOURCE_SHA256}")
    return data.decode("utf-8", errors="replace").splitlines()


def candidates(lines):
    """(line number, FEN) for every orthodox, legal position with White to move, in a fixed shuffled order."""
    found = []
    for number, line in enumerate(lines, start=1):
        placement = line.strip()
        if not placement or "(" in placement:
            continue
        fen = f"{placement} w - - 0 1"
        try:
            parse_fen(fen)
        except ValueError:
            continue
        found.append((number, fen))
    random.Random(SEED).shuffle(found)
    return found


def solve(fen):
    """The position's shortest forced mate within max(LENGTHS) moves, its keys and a main line."""
    position = parse_fen(fen)
    n = shortest_mate(position, max(LENGTHS))
    if n is None:
        return None
    keys = mating_keys(position, n)
    for key in keys:
        assert forces_mate(position, parse_uci(position, key), n)
    return {"mate_in": n, "keys": keys, "main_line": main_line(position, keys[0], n)}


def _work(tasks, results):
    while (task := tasks.get()) is not None:
        index, fen = task
        results.put((index, solve(fen)))


def solve_all(found, workers):
    """Solve candidates in order across worker processes until each mate length has PER_LENGTH puzzles."""
    results = multiprocessing.Queue()
    pool = {}  # worker id -> [process, its task queue, (index, started) or None]

    def spawn(worker):
        tasks = multiprocessing.Queue()
        process = multiprocessing.Process(target=_work, args=(tasks, results), daemon=True)
        process.start()
        pool[worker] = [process, tasks, None]

    for worker in range(workers):
        spawn(worker)
    solved, next_index, reported = {}, 0, 0

    def enough():
        # Enough once the solved prefix of the order holds PER_LENGTH of each length.
        counts, index = dict.fromkeys(LENGTHS, 0), 0
        while index in solved:
            outcome = solved[index]
            if outcome:
                counts[outcome["mate_in"]] += 1
            index += 1
        return all(count >= PER_LENGTH for count in counts.values())

    while next_index < len(found) or any(slot[2] for slot in pool.values()):
        for worker, slot in pool.items():
            if slot[2] is None and next_index < len(found):
                slot[1].put((next_index, found[next_index][1]))
                slot[2] = (next_index, time.monotonic())
                next_index += 1
        try:
            index, outcome = results.get(timeout=0.2)
            solved[index] = outcome
            for slot in pool.values():
                if slot[2] and slot[2][0] == index:
                    slot[2] = None
        except queue.Empty:
            pass
        for worker, slot in list(pool.items()):
            if slot[2] and time.monotonic() - slot[2][1] > SEARCH_LIMIT:
                solved[slot[2][0]] = None
                slot[0].terminate()
                spawn(worker)
        if len(solved) // 200 > reported:
            reported = len(solved) // 200
            print(f"{len(solved)} candidates tried", flush=True)
        if enough():
            break
    for process, tasks, _ in pool.values():
        process.terminate()
    return solved


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", help="a local copy of the pinned .fen file (downloaded if omitted)")
    parser.add_argument("--workers", type=int, default=max(1, multiprocessing.cpu_count() - 1))
    args = parser.parse_args()
    found = candidates(read_source(args.source))
    print(f"{len(found)} orthodox candidates", flush=True)
    solved = solve_all(found, args.workers)
    puzzles, counts, index = [], dict.fromkeys(LENGTHS, 0), 0
    while index in solved:
        outcome = solved[index]
        if outcome:
            n = outcome["mate_in"]
            if counts[n] < PER_LENGTH:
                counts[n] += 1
                number, fen = found[index]
                puzzles.append(
                    {
                        "id": f"m{n}-{counts[n]:04d}",
                        "fen": fen,
                        "mate_in": n,
                        "keys": outcome["keys"],
                        "main_line": outcome["main_line"],
                        "source_line": number,
                    }
                )
        index += 1
    puzzles.sort(key=lambda puzzle: puzzle["id"])
    document = {
        "source": {"url": SOURCE_URL, "sha256": SOURCE_SHA256, "seed": SEED, "credit": "yacpdb.org"},
        "puzzles": puzzles,
    }
    OUTPUT.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {counts} puzzles to {OUTPUT}")


if __name__ == "__main__":
    main()
