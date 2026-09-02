import threading
import time
import uuid


SESSION_TIMEOUT_SECONDS = 20
MIN_PLAYERS = 2
MAX_PLAYERS = 4
VALID_ROLES = {"host", "join"}
VALID_GUEST_PLAYERS = {2, 3, 4}


class MultiplayerSessionRegistry:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._sessions = {}

    def host(self, game, lobby_name="LAN Game", max_players=3):
        self._validate_game(game)
        lobby_name = self._validate_lobby_name(lobby_name)
        max_players = self._validate_max_players(max_players)
        now = self._clock()
        session = {
            "id": uuid.uuid4().hex,
            "token": uuid.uuid4().hex,
            "lobbyName": lobby_name,
            "maxPlayers": max_players,
            "game": dict(game),
            "playerHeartbeats": {1: now},
            "updated": now,
        }
        with self._lock:
            self._sessions[session["id"]] = session
        return self._public(session, include_token=True)

    def join(self, session_id, player):
        player = self._validate_guest_player(player)
        with self._lock:
            session = self._get_active_session(session_id)
            if player > session["maxPlayers"]:
                raise ValueError("That lobby does not support the selected player.")
            if player > 2 and player - 1 not in session["playerHeartbeats"]:
                raise ValueError(f"Player {player - 1} must join before Player {player}.")
            session["playerHeartbeats"][player] = self._clock()
            return self._public(session)

    def heartbeat(self, session_id, token, role, player=2):
        if role not in VALID_ROLES:
            raise ValueError("Invalid multiplayer role.")
        with self._lock:
            session = self._get_active_session(session_id)
            if role == "host":
                if session["token"] != token:
                    raise PermissionError("Host authorization failed.")
                player = 1
                session["updated"] = self._clock()
            else:
                player = self._validate_guest_player(player)
                if player > session["maxPlayers"]:
                    raise ValueError("That player slot is not available.")
            session["playerHeartbeats"][player] = self._clock()
            return self._public(session)

    def sessions(self):
        with self._lock:
            self._remove_expired_sessions()
            return [self._public(session) for session in self._sessions.values()]

    def current(self):
        sessions = self.sessions()
        return sessions[0] if sessions else {"active": False}

    def close(self, session_id, token):
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            if session["token"] != token:
                raise PermissionError("Host authorization failed.")
            del self._sessions[session_id]
            return True

    def _get_active_session(self, session_id):
        self._remove_expired_sessions()
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError("The multiplayer session is no longer active.")
        return session

    def _remove_expired_sessions(self):
        now = self._clock()
        expired = [session_id for session_id, session in self._sessions.items()
                   if now - session["updated"] > SESSION_TIMEOUT_SECONDS]
        for session_id in expired:
            del self._sessions[session_id]
        for session in self._sessions.values():
            stale_guests = [
                player
                for player, heartbeat in session["playerHeartbeats"].items()
                if player != 1 and now - heartbeat > SESSION_TIMEOUT_SECONDS
            ]
            for player in stale_guests:
                del session["playerHeartbeats"][player]

    @staticmethod
    def _validate_game(game):
        required = ("core", "path", "name")
        if not isinstance(game, dict) or any(not str(game.get(field, "")).strip()
                                             for field in required):
            raise ValueError("A valid game is required to host multiplayer.")
        if ".." in game["path"]:
            raise ValueError("Invalid game path.")

    @staticmethod
    def _validate_lobby_name(lobby_name):
        name = str(lobby_name or "").strip()
        if not name or len(name) > 40:
            raise ValueError("Lobby name must contain 1 to 40 characters.")
        return name

    @staticmethod
    def _validate_max_players(max_players):
        value = int(max_players)
        if value < MIN_PLAYERS or value > MAX_PLAYERS:
            raise ValueError("Lobby size must be between 2 and 4 players.")
        return value

    @staticmethod
    def _validate_guest_player(player):
        value = int(player)
        if value not in VALID_GUEST_PLAYERS:
            raise ValueError("Guest player must be Player 2, 3, or 4.")
        return value

    @staticmethod
    def _public(session, include_token=False):
        joined_players = sorted(session["playerHeartbeats"])
        response = {
            "active": True,
            "id": session["id"],
            "lobbyName": session["lobbyName"],
            "maxPlayers": session["maxPlayers"],
            "game": dict(session["game"]),
            "players": len(joined_players),
            "joinedPlayers": joined_players,
        }
        if include_token:
            response["token"] = session["token"]
        return response
