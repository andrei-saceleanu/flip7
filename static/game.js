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
  socket.emit("freeze_target", { target_sid: sid });
}


socket.on("connect", () => {
  if (savedGameCode) {
    socket.emit("rejoin_game", {
      code: savedGameCode,
      player_id: playerId
    });
  }
});

socket.on("state", state => {
  menu = document.getElementById("menu")
  game = document.getElementById("game")
  codeDisplay = document.getElementById("codeDisplay")
  roundDisplay = document.getElementById("roundDisplay")
  startBtn = document.getElementById("startBtn")

  menu.style.display = "none";
  game.style.display = "block";
  codeDisplay.innerText = "Game Code: " + state.code;
  roundDisplay.innerText = "Round: " + state.round;

  players = document.getElementById("players")
  players.innerHTML = "";

  state.players.forEach((p, i) => {
    if (state.code) {
      sessionStorage.setItem("game_code", state.code);
    }

    const div = document.createElement("div");
    div.className = "player";
    if (state.turn === i && state.started) div.classList.add("active");

    const cards = p.cards.map(c => {
      if (c.type === "number") return `<div class="card">${c.value}</div>`;
      if (c.type === "second_chance") return `<div class="card">🔁</div>`;
      if (c.type === "freeze") return `<div class="card">❄️${c.target ?? ""}</div>`;
    }).join("");

    const freezeBtn =
      state.pending_freeze === socket.id && !p.finished
        ? `<button onclick="freezeTarget('${p.sid}')">Freeze</button>`
        : "";

    div.innerHTML = `
      <h3>${p.name}</h3>
      <div>Round: ${p.round_score}</div>
      <div>Total: ${p.total_score}</div>
      <div class="cards">${cards}</div>
      ${freezeBtn}
    `;
    players.appendChild(div);
  });

  startBtn.style.display = state.started ? "none" : "inline";

  if (state.match_winner) {
    alert(`🏆 ${state.match_winner} wins the match!`);
    sessionStorage.removeItem("game_code");
  }
});

socket.on("error", alert);
