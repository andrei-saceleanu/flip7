const socket = io();

const nameInput = document.getElementById('name');
const codeInput = document.getElementById('code');

let playerId = sessionStorage.getItem("player_id");
if (!playerId) {
  playerId = crypto.randomUUID();
  sessionStorage.setItem("player_id", playerId);
}

const savedGameCode = sessionStorage.getItem("game_code");

function createGame() {
  socket.emit("create_game", { name: nameInput.value, player_id: playerId});
}

function joinGame() {
  socket.emit("join_game", { name: nameInput.value, code: codeInput.value, player_id: playerId});
}

function startGame() {
  socket.emit("start_game");
}

function hit() {
  socket.emit("hit");
}

function stay() {
  socket.emit("stay");
}

function freezeTarget(sid) {
  controlsLocked = true;
  socket.emit("freeze_target", { target_sid: sid });
}

function flip3Target(sid) {
  controlsLocked = true;
  socket.emit("flip3_target", { target_sid: sid});
}

function discardChooseTarget(targetSid, cardIdx) {
  controlsLocked = true;
  socket.emit("discard_choose_target", { target_sid: targetSid, card_idx: cardIdx });
}
function discardChooseCard(cardIdx) {
  controlsLocked = true;
  socket.emit("discard_choose_card", { card_idx: cardIdx });
}


let controlsLocked = false;

socket.on("connect", () => {
  if (savedGameCode) {
    socket.emit("rejoin_game", {
      code: savedGameCode,
      player_id: playerId
    });
  }
});

socket.on("state", state => {
  let menu = document.getElementById("menu");
  let game = document.getElementById("game");
  let codeDisplay = document.getElementById("codeDisplay");
  let roundDisplay = document.getElementById("roundDisplay");
  let startBtn = document.getElementById("startBtn");

  menu.style.display = "none";
  game.style.display = "block";
  codeDisplay.innerText = "Game Code: " + state.code;
  roundDisplay.innerText = "Round: " + state.round;

  let players = document.getElementById("players");
  players.innerHTML = "";

  let myIdx = -1;
  let mySid = socket.id;

  state.players.forEach((p, i) => {
    if (p.sid === mySid) {
      myIdx = i;
    }
    if (state.code) {
      sessionStorage.setItem("game_code", state.code);
    }

    const div = document.createElement("div");
    div.className = "player";
    if (state.turn === i && state.started) div.classList.add("active");

    // Detect if this is our hand AND we're being prompted to discard
    let myTurnToDiscard = state.pending_discard_choose_card === socket.id && !p.finished && p.sid === socket.id;

    // --- Card rendering ---
    let cards = p.cards.map((c, cidx) => {
      let display;
      if (c.type === "number") display = c.value;
      else if (c.type === "second_chance") display = "🔁";
      else if (c.type === "flip_three") display = `3️⃣${c.target ?? ""}`;
      else if (c.type === "freeze") display = `❄️${c.target ?? ""}`;
      else if (c.type === "bonus") display = c.value;
      else if (c.type === "discard") display = `🗑️${c.target ?? ""}`;
      else display = c.type;

      if (myTurnToDiscard && c.type === "number") {
        // Make each card clickable for discarding
        return `<div class="card clickable" onclick="discardChooseCard(${cidx})">${display}</div>`;
      } else {
        return `<div class="card">${display}</div>`;
      }
    }).join("");

    const discardNotice = myTurnToDiscard ? "<b>Discard one of the highlighted cards:</b>" : "";

    // --- Action Buttons ---
    const freezeBtn =
      state.pending_freeze === socket.id && !p.finished
        ? `<button onclick="freezeTarget('${p.sid}')">Freeze</button>`
        : "";

    const flip3Btn =
      state.pending_flip3 === socket.id && !p.finished
        ? `<button onclick="flip3Target('${p.sid}')">Make flip 3</button>`
        : "";

    let discardStep = "";

    // Step 1: If we're the player who must choose the DISCARD target
    if (state.pending_discard_choose_target === socket.id && !p.finished && p.sid === socket.id) {
      const cardIdx = state.discard_choose_target_info.card_idx;
      const selectable = state.players.filter(q => !q.finished && q.cards.length > 0);
      discardStep = `<div>
        <b>Choose a player to discard one:</b><br>
        ${selectable.map(pl =>
          `<button onclick="discardChooseTarget('${pl.sid}', ${cardIdx})">${pl.name === p.name ? pl.name + " (you)" : pl.name}</button>`
        ).join(" ")}
      </div>`;
    }

    div.innerHTML = `
      <h3>${p.name}</h3>
      <div>Round score: ${p.round_score}</div>
      <div>Total score: ${p.total_score}</div>
      ${discardNotice}
      <div class="cards">${cards}</div>
      ${freezeBtn}
      ${flip3Btn}
      ${discardStep}
    `;
    players.appendChild(div);
  });

  let hitBtn = document.querySelector('button[onclick="hit()"]');
  let stayBtn = document.querySelector('button[onclick="stay()"]');

  if ('end_pending' in state) {
    controlsLocked = false;
  }
  // Only the current player whose turn it is, and game started, can use buttons
  const myTurn = state.turn === myIdx && state.started;
  // Disable controls if it's not your turn, or if an action prompt is pending
  const controlsDisabled =
    !myTurn ||
    controlsLocked ||
    state.pending_freeze == socket.id ||
    state.pending_flip3 == socket.id ||
    state.pending_discard_choose_target == socket.id ||
    state.pending_discard_choose_card != null;

  if (hitBtn) hitBtn.disabled = controlsDisabled;
  if (stayBtn) stayBtn.disabled = controlsDisabled;

  startBtn.style.display = state.started ? "none" : "inline";

  if (state.match_winner) {
    alert(`🏆 ${state.match_winner} wins the match!`);
    sessionStorage.removeItem("game_code");
  }
});

socket.on("error", alert);
