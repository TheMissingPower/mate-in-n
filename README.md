# Mate in N

A `nanoagent.plugin/v0001` plugin. An agent is given a composed chess problem in which White to move forces
checkmate within n moves (n is 1, 2 or 3). The agent must find the **key**, White's first move that mates within n
however Black defends, and show one main line that ends in checkmate. A deterministic verifier proves the answer
with its own chess rules. No model judges anything.

The puzzles are 300 problems (100 each of mate in 1, 2 and 3) from the
[432k-chess-puzzles](https://github.com/rebeccaloran/432k-chess-puzzles) collection of
[yacpdb.org](https://www.yacpdb.org/) problems, solved ahead of time and bundled in
`src/plugin/data/puzzles.json`. The plugin needs no network and no API key.

## Tools

| Tool | Does | Code |
|---|---|---|
| `get_puzzle` | Gives a puzzle's starting FEN, a board diagram and n | `src/plugin/puzzles.py` |
| `legal_moves` | Lists a position's legal moves in UCI and SAN, with check, mate and stalemate flags | `src/plugin/board.py` |
| `play_moves` | Plays 1 to 12 UCI moves from a FEN and returns the new FEN and flags; refuses an illegal move | `src/plugin/board.py` |
| `solve_puzzle` | Gives every key that forces mate within n (the task's reference, never shown to the agent) | `src/plugin/puzzles.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `solve-mate` | Finds the key and a main line of a mate-in-n puzzle given by id, such as `m2-0042` | `agent`, with `get_puzzle`, `legal_moves`, `play_moves`; reference `solve_puzzle` |

**Input** `{puzzle_id}`. **Output** `{puzzle_id, key_move, main_line}`, with moves in UCI (`e2e4`, `e7e8q`).

**Success.** The verifier (`verifier/solve.py`) checks these in order. The first that fails decides the verdict.

| Check | Fails with score |
|---|---|
| The answer is for the task's puzzle | 0 |
| `key_move` is a well-formed UCI move | 0 |
| `key_move` is legal in the puzzle | 0 |
| `key_move` forces mate within n against every Black defence, proved by the verifier's exhaustive search and matching the reference's key list (a disagreement is reported as an integrity failure) | 0 |
| `main_line` starts with the key, every move is legal, it is at most 2n - 1 moves long, and it ends with Black checkmated | 0.5 |

An answer that passes every check is valid, with score 1. Any key that forces mate within n is accepted, including
a second solution ("cook") of the original problem. Every bundled puzzle has no shorter mate.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs (none)
├── src/plugin/      # the MCP server: __main__.py and its IMPLEMENTATIONS, puzzles.py, board.py
│   ├── chess_rules.py   # pure standard-library chess rules and forced-mate search
│   ├── data/puzzles.json
│   └── tools_dev/build_puzzles.py   # rebuilds data/puzzles.json from the pinned source
├── tests/
├── ui/              # renderers.js and renderers.css: outputs are drawn from their JSON Schema
├── product/         # product.yaml and icon.svg
└── verifier/        # deterministic verifier: puzzle.py, board.py, solve.py, and a copy of chess_rules.py
```

The verifier may import only the standard library, so it can't use a chess library. `chess_rules.py` is written for
this plugin and kept as two identical copies, one in `src/plugin/` and one in `verifier/`. A test fails if they
differ. The rules are tested against the standard perft move counts of six reference positions.

**How the puzzles are made.** The source file gives only each problem's piece placement.
`tools_dev/build_puzzles.py` works through it as follows:

1. It reads the file at a pinned commit and checks its SHA-256.
2. It drops positions with fairy pieces and impossible positions.
3. It sets every position to White to move, with no castling and no en passant, the direct-mate convention.
4. It shuffles the positions with a fixed seed.
5. It searches each position for its shortest forced mate. It keeps exact mates in 1, 2 and 3, with every key
   recorded. A mate in 3 is kept only if all its keys can be proved quickly.

## Develop and run

```bash
uv sync --extra dev
uv run pytest          # MATE_SLOW=1 uv run pytest also re-proves every stored mate-in-3 key
uv run ruff check .
```

To rebuild the puzzles (this needs the network, or a local copy of the pinned file passed with `--source`):

```bash
uv run python -m plugin.tools_dev.build_puzzles
```

Publishing checks every plugin rule: push the plugin to a public GitHub repository and submit its URL on
RUSH Lab.

**Limitations.**
- Every puzzle is played with White to move, no castling and no en passant. A problem whose original solution
  needs one of those can have a different solution here than in the original. The bundled keys are always computed
  under this plugin's convention.
- The 50-move and repetition rules are ignored, which can't matter within 3 moves.
- The source collection has no license. Only a small, credited subset is bundled.
