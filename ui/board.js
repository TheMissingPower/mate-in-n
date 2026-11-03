// A chess board for the renderers: a FEN's position, UCI moves played on it, and the board drawn
// as a grid of squares. Only what a drawing needs: the moves were already checked by the verifier.

import { h } from "./kit/components.js";

const FILES = "abcdefgh";
// Solid glyphs for both sides, coloured by renderers.css; U+FE0E keeps each a text glyph, never an emoji.
const GLYPHS = { k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟" };
const NAMES = { k: "king", q: "queen", r: "rook", b: "bishop", n: "knight", p: "pawn" };

/** The position of a FEN: `squares`, 64 pieces or null from a8 to h1, and whether White is to move. */
export function parseFen(fen) {
  const [placement, side = "w"] = String(fen).trim().split(/\s+/);
  const squares = [];
  for (const char of placement.replaceAll("/", "")) {
    if (/\d/.test(char)) squares.push(...Array(Number(char)).fill(null));
    else squares.push(char);
  }
  if (squares.length !== 64) throw new Error(`not a FEN: ${fen}`);
  return { squares, white: side === "w" };
}

/** The index in `squares` of a square such as "e4". */
export function squareIndex(name) {
  return (8 - Number(name[1])) * 8 + FILES.indexOf(name[0]);
}

/** The position after the UCI move `text`, such as "e2e4" or "e7e8q": promotion, castling and en passant included. */
export function playUci(position, text) {
  const from = squareIndex(text.slice(0, 2));
  const to = squareIndex(text.slice(2, 4));
  const squares = [...position.squares];
  const piece = squares[from];
  if (!piece) throw new Error(`no piece on ${text.slice(0, 2)}`);
  const kind = piece.toLowerCase();
  const sideways = (to % 8) - (from % 8);
  if (kind === "p" && sideways !== 0 && !squares[to]) squares[from - (from % 8) + (to % 8)] = null;
  if (kind === "k" && Math.abs(sideways) === 2) {
    const [rookFrom, rookTo] = sideways > 0 ? [to + 1, to - 1] : [to - 2, to + 1];
    squares[rookTo] = squares[rookFrom];
    squares[rookFrom] = null;
  }
  const promotion = text[4];
  squares[to] = promotion ? (piece === "P" ? promotion.toUpperCase() : promotion) : piece;
  squares[from] = null;
  return { squares, white: !position.white };
}

/** Every position of `moves` from `fen`: the start, then one after each move. Stops at a move it cannot play. */
export function positions(fen, moves) {
  const all = [parseFen(fen)];
  for (const move of moves) {
    try {
      all.push(playUci(all[all.length - 1], move));
    } catch {
      break;
    }
  }
  return all;
}

/**
 * The board drawn: 8 by 8 squares, rank 8 at the top, with file and rank labels.
 * @param {{squares: (string|null)[]}} position
 * @param {{move?: string, label?: string}} [options] `move` highlights its from and to squares.
 */
export function drawBoard(position, { move, label } = {}) {
  const marked = move ? [squareIndex(move.slice(0, 2)), squareIndex(move.slice(2, 4))] : [];
  const cells = position.squares.map((piece, index) => {
    const file = index % 8;
    const rank = 8 - Math.floor(index / 8);
    const name = `${FILES[file]}${rank}`;
    // a1 is dark.
    const shade = (file + rank) % 2 === 1 ? "dark" : "light";
    const classes = ["square", shade, marked.includes(index) ? "moved" : "", piece ? (piece === piece.toUpperCase() ? "white" : "black") : ""];
    const title = piece ? `${piece === piece.toUpperCase() ? "White" : "Black"} ${NAMES[piece.toLowerCase()]} on ${name}` : name;
    return h(
      "div",
      { class: classes.filter(Boolean).join(" "), title, role: "gridcell", "aria-label": title },
      piece ? h("span", { class: "piece", text: `${GLYPHS[piece.toLowerCase()]}︎` }) : null,
      file === 0 ? h("span", { class: "rank-label", text: String(rank) }) : null,
      rank === 1 ? h("span", { class: "file-label", text: FILES[file] }) : null,
    );
  });
  return h("div", { class: "board", role: "grid", "aria-label": label || "Chess board" }, cells);
}
