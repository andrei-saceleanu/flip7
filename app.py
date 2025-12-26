from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
from game import Game

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"
socketio = SocketIO(app, cors_allowed_origins="*")

games = {}
player_game = {}

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("create_game")
def create_game(data):
    game = Game(owner_sid=request.sid)
    game.add_player(data["name"], request.sid)
    games[game.code] = game
    player_game[request.sid] = game.code
    join_room(game.code)
    emit("state", game.to_dict())

@socketio.on("join_game")
def join_game(data):
    code = data["code"]
    if code not in games:
        emit("error", "Game not found")
        return

    game = games[code]
    if not game.add_player(data["name"], request.sid):
        emit("error", "Game already started")
        return

    player_game[request.sid] = code
    join_room(code)
    socketio.emit("state", game.to_dict(), room=code)

@socketio.on("start_game")
def start_game():
    code = player_game.get(request.sid)
    game = games.get(code)
    if game and game.start(request.sid):
        socketio.emit("state", game.to_dict(), room=code)

@socketio.on("hit")
def hit():
    code = player_game.get(request.sid)
    game = games.get(code)
    if game:
        game.hit(request.sid)
        socketio.emit("state", game.to_dict(), room=code)

@socketio.on("stay")
def stay():
    code = player_game.get(request.sid)
    game = games.get(code)
    if game:
        game.stay(request.sid)
        socketio.emit("state", game.to_dict(), room=code)

@socketio.on("freeze_target")
def freeze_target(data):
    game = games.get(player_game.get(request.sid))
    if game:
        game.apply_freeze(request.sid, data["target_sid"])
        socketio.emit("state", game.to_dict(), room=game.code)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", debug=True)
