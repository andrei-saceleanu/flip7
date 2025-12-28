from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
from game import Game

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"
socketio = SocketIO(app, cors_allowed_origins="*")

games = {}          # code -> Game
player_game = {}    # sid -> code


@app.route("/")
def index():
    return render_template("index.html")


# ---------- Game creation / joining ----------

@socketio.on("create_game")
def create_game(data):
    game = Game(owner_sid=request.sid)
    game.add_player(
        data["name"],
        request.sid,
        data.get("player_id")
    )

    games[game.code] = game
    player_game[request.sid] = game.code
    join_room(game.code)

    emit("state", game.to_dict())


@socketio.on("join_game")
def join_game(data):
    game = games.get(data["code"])
    if not game:
        emit("error", "Game not found")
        return

    player = game.add_player(
        data["name"],
        request.sid,
        data.get("player_id")
    )

    if not player:
        emit("error", "Unable to join")
        return

    player_game[request.sid] = game.code
    join_room(game.code)
    socketio.emit("state", game.to_dict(), room=game.code)


@socketio.on("rejoin_game")
def rejoin_game(data):
    game = games.get(data["code"])
    if not game:
        return

    player = game.get_player_by_player_id(data["player_id"])
    if not player:
        return

    player.sid = request.sid
    player_game[request.sid] = game.code
    join_room(game.code)

    emit("state", game.to_dict(), room=game.code)


@socketio.on("start_game")
def start_game():
    game = games.get(player_game.get(request.sid))
    if game and game.start(request.sid):
        socketio.emit("state", game.to_dict(), room=game.code)


# ---------- Gameplay ----------

@socketio.on("hit")
def hit():
    game = games.get(player_game.get(request.sid))
    if game:
        game.hit(request.sid)
        socketio.emit("state", game.to_dict(), room=game.code)


@socketio.on("stay")
def stay():
    game = games.get(player_game.get(request.sid))
    if game:
        game.stay(request.sid)
        socketio.emit("state", game.to_dict(), room=game.code)


@socketio.on("freeze_target")
def freeze_target(data):
    game = games.get(player_game.get(request.sid))
    if game:
        game.apply_freeze(request.sid, data["target_sid"])
        resp = game.to_dict()
        resp.update({"end_pending": True})
        socketio.emit("state", resp, room=game.code)

@socketio.on("flip3_target")
def flip3_target(data):
    game = games.get(player_game.get(request.sid))
    if game:
        partial_states = game.apply_flip3(request.sid, data["target_sid"])
        for idx, elem in enumerate(partial_states):
            socketio.emit("state", elem, room=game.code)
            if idx < len(partial_states)-1:
                socketio.sleep(1)
        resp = game.to_dict()
        resp.update({"end_pending": True})
        socketio.emit("state", resp, room=game.code)



# ---------- Disconnect handling ----------

@socketio.on("disconnect")
def disconnect():
    code = player_game.pop(request.sid, None)
    if not code:
        return

    game = games.get(code)
    if not game:
        return

    # Remove sid mapping only (player object stays for reconnect)
    for p in game.players:
        if p.sid == request.sid:
            p.sid = None

    socketio.emit("state", game.to_dict(), room=code)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", debug=True)
