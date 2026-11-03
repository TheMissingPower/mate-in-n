// How this plugin's page draws its tasks' outputs: a puzzle as its starting board, and an answer as
// a board to step through, from the start to the last move of the main line.

import { h } from "./kit/components.js";
import { drawBoard, parseFen, positions, squareIndex } from "./board.js";

const PIECES = { k: "King", q: "Queen", r: "Rook", b: "Bishop", n: "Knight", p: "Pawn" };

/** A move's label, such as "1. Queen d1 → h5" or "1… Pawn e7 → e5", from the position it is played in. */
function moveLabel(position, move, index) {
  const piece = position.squares[squareIndex(move.slice(0, 2))];
  const name = piece ? PIECES[piece.toLowerCase()] : "";
  const promotion = move[4] ? ` = ${PIECES[move[4]]}` : "";
  const number = `${Math.floor(index / 2) + 1}${index % 2 === 0 ? "." : "…"}`;
  return `${number} ${name} ${move.slice(0, 2)} → ${move.slice(2, 4)}${promotion}`;
}

/** The moves as plain text, for an answer whose start the verdict does not give. */
function movesText(answer) {
  return h("p", { class: "moves-text", text: `Key ${answer.key_move}; main line ${(answer.main_line || []).join(" ") || "none"}` });
}

function solution(answer, { verdict }) {
  const fen = verdict?.details?.fen;
  if (!fen) return movesText(answer);
  const line = answer.main_line || [];
  const steps = positions(fen, line);
  const mated = Boolean(verdict.valid);
  let shown = steps.length - 1;

  const boardSlot = h("div", { class: "board-slot" });
  const caption = h("p", { class: "caption", "aria-live": "polite" });
  const prev = h("button", { type: "button", class: "button small ghost", text: "← Prev", onclick: () => show(shown - 1) });
  const next = h("button", { type: "button", class: "button small ghost", text: "Next →", onclick: () => show(shown + 1) });
  const chips = steps.map((_, index) =>
    h("button", {
      type: "button",
      class: "move-chip",
      text: index === 0 ? "Start" : moveLabel(steps[index - 1], line[index - 1], index - 1),
      onclick: () => show(index),
    }),
  );

  function show(index) {
    shown = Math.max(0, Math.min(steps.length - 1, index));
    const move = shown > 0 ? line[shown - 1] : undefined;
    boardSlot.replaceChildren(drawBoard(steps[shown], { move, label: `Position after ${shown} moves` }));
    const last = shown === steps.length - 1 && shown > 0;
    caption.textContent =
      shown === 0
        ? "Start: White to move"
        : `${chips[shown].textContent}${last && mated ? " — checkmate" : ""}`;
    chips.forEach((chip, at) => chip.classList.toggle("current", at === shown));
    prev.disabled = shown === 0;
    next.disabled = shown === steps.length - 1;
  }

  show(shown);
  return h(
    "div",
    { class: "mate-answer" },
    h("p", { class: "summary" }, "Key move ", h("strong", { text: answer.key_move }), ` · puzzle ${answer.puzzle_id}`),
    boardSlot,
    caption,
    h("div", { class: "stepper" }, prev, next),
    h("div", { class: "move-list" }, chips),
  );
}

function puzzle(value, { send }) {
  return h(
    "div",
    { class: "mate-puzzle" },
    h("p", { class: "summary" }, h("strong", { text: value.puzzle_id }), ` · White to move and mate in ${value.mate_in}`),
    h("div", { class: "board-slot" }, drawBoard(parseFen(value.fen), { label: `Puzzle ${value.puzzle_id}` })),
    h("button", {
      type: "button",
      class: "button small primary",
      text: "Solve it",
      onclick: () => send(`Solve puzzle ${value.puzzle_id}`),
    }),
  );
}

export default { PuzzleOutput: puzzle, SolveMateOutput: solution };
