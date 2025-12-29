# Repository Guidelines

## Project Structure & Module Organization
- `app.py`: Flask + Socket.IO entrypoint; owns routing and socket events.
- `game.py`: Core Flip 7 rules and state (Game/Player/Deck); keep game logic here and treat it as framework-agnostic.
- `templates/index.html`: Minimal UI shell.
- `static/game.js` & `static/style.css`: Client behavior and presentation; prefer small, targeted DOM updates and keep game state read-only on the client.

## Setup, Build, and Run
- Use Python 3.10+; create a virtualenv before installing dependencies.
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install flask flask-socketio eventlet`
- Run locally: `python app.py` (serves on 0.0.0.0 with debug enabled). Open two browser tabs to simulate players.
- If adding packages, freeze versions in a new `requirements.txt` and pin exact versions.

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indents, snake_case for functions/variables, PascalCase for classes. Keep side effects inside Flask/socket handlers; keep pure calculations in `game.py` where possible.
- JavaScript: `const`/`let`, camelCase functions, avoid global state beyond the existing socket/game cache. Keep UI strings short and avoid inline HTML where a helper function suffices.
- Templates/CSS: Keep markup semantic and minimal; prefer class-based styling over inline styles.

## Testing Guidelines
- Automated tests are not yet present; prefer `pytest` for new coverage. Place tests under `tests/` and name files `test_*.py`, targeting pure game logic (`game.py`) first.
- Manual smoke flow: start the server, open two tabs, create a game, join, start, exercise Hit/Stay, Freeze, Flip 3, and reconnect (refresh) to confirm state restoration.

## Commit & Pull Request Guidelines
- Commits: short, imperative subjects (e.g., "fix flip3 target lock"), mirroring existing history. Scope each commit to one concern.
- PRs: include a brief summary, testing notes (commands run or manual steps), and screenshots/GIFs for UI changes. Link related issues and call out any behavior changes or new dependencies.

## Security & Configuration Tips
- The default `SECRET_KEY` in `app.py` is for local use only; set a real secret via environment variable before deployment.
- Avoid storing secrets in the repo. If adding configuration, prefer environment variables or `.env` (gitignored).
