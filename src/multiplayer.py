import threading
import time
import uuid


SESSION_TIMEOUT_SECONDS = 20
VALID_ROLES = {"host", "join"}


class MultiplayerSessionRegistry:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._session = None

    def host(self, game):
        self._validate_game(game)
        session = {
            "id": uuid.uuid4().hex,
            "token": uuid.uuid4().hex,
            "game": dict(game),
            "players": 1,
            "updated": self._clock(),
        }
        with self._lock:
            self._session = session
        return self._public(session, include_token=True)

    def heartbeat(self, session_id, token, role):
        if role not in VALID_ROLES:
            raise ValueError("Invalid multiplayer role.")
        with self._lock:
            session = self._active_session()
            if not session or session["id"] != session_id:
                raise ValueError("The multiplayer session is no longer active.")
            if role == "host" and session["token"] != token:
                raise PermissionError("Host authorization failed.")
            session["updated"] = self._clock()
            if role == "join":
                session["players"] = 2
            return self._public(session)

    def current(self):
        with self._lock:
            session = self._active_session()
            return self._public(session) if session else {"active": False}

    def close(self, session_id, token):
        with self._lock:
            session = self._active_session()
            if not session or session["id"] != session_id:
                return False
            if session["token"] != token:
                raise PermissionError("Host authorization failed.")
            self._session = None
            return True

    def _active_session(self):
        if self._session and self._clock() - self._session["updated"] > SESSION_TIMEOUT_SECONDS:
            self._session = None
        return self._session

    @staticmethod
    def _validate_game(game):
        required = ("core", "path", "name")
        if not isinstance(game, dict) or any(not str(game.get(field, "")).strip() for field in required):
            raise ValueError("A valid game is required to host multiplayer.")
        if ".." in game["path"]:
            raise ValueError("Invalid game path.")

    @staticmethod
    def _public(session, include_token=False):
        response = {
            "active": True,
            "id": session["id"],
            "game": dict(session["game"]),
            "players": session["players"],
        }
        if include_token:
            response["token"] = session["token"]
        return response
