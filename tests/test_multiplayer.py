import os
import unittest

from src.multiplayer import MultiplayerSessionRegistry


ROOT = os.path.join(os.path.dirname(__file__), "..")


class FakeClock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now


class MultiplayerRegistryTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.registry = MultiplayerSessionRegistry(self.clock)
        self.game = {"core": "snes", "path": "snes/game.zip", "name": "Game",
                     "origin": "http://192.168.0.148:8080"}

    def test_host_guest_heartbeat_and_host_close(self):
        hosted = self.registry.host(self.game)
        self.assertEqual(hosted["players"], 1)
        joined = self.registry.heartbeat(hosted["id"], "", "join")
        self.assertEqual(joined["players"], 2)
        self.assertTrue(self.registry.close(hosted["id"], hosted["token"]))
        self.assertEqual(self.registry.current(), {"active": False})

    def test_session_expires_without_host_heartbeat(self):
        self.registry.host(self.game)
        self.clock.now = 21
        self.assertEqual(self.registry.current(), {"active": False})

    def test_host_actions_require_private_token(self):
        hosted = self.registry.host(self.game)
        with self.assertRaises(PermissionError):
            self.registry.heartbeat(hosted["id"], "wrong", "host")
        with self.assertRaises(PermissionError):
            self.registry.close(hosted["id"], "wrong")


class MultiplayerUiTests(unittest.TestCase):
    def test_library_exposes_host_join_and_auto_discovery(self):
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as source:
            page = source.read()
        with open(os.path.join(ROOT, "web", "multiplayer.js"), encoding="utf-8") as source:
            script = source.read()
        self.assertIn("Experimental Multiplayer", page)
        self.assertIn('data-multiplayer-mode="host"', page)
        self.assertIn('data-multiplayer-mode="join"', page)
        self.assertIn("/api/multiplayer/session", script)
        self.assertIn("location.replace(joinUrl(session))", script)

    def test_play_page_enables_and_automates_emulatorjs_netplay(self):
        with open(os.path.join(ROOT, "web", "play.html"), encoding="utf-8") as source:
            page = source.read()
        self.assertIn("window.EJS_EXPERIMENTAL_NETPLAY=true", page)
        self.assertIn("window.EJS_netplayServer=NETPLAY_SERVER", page)
        self.assertIn("emulator.netplay.openRoom(multiplayerSession,2,'')", page)
        self.assertIn("room.room_name===multiplayerSession", page)
        self.assertIn("emulator.netplay.joinRoom(roomId,room.room_name)", page)
        self.assertIn("Player 1", page)
        self.assertIn("Player 2", page)
        self.assertIn("startupRestart='multiplayer-skip'", page)
        self.assertIn("session?.players===2", page)

    def test_installer_copies_multiplayer_components(self):
        with open(os.path.join(ROOT, "install.sh"), encoding="utf-8") as source:
            installer = source.read()
        self.assertIn('src/multiplayer.py', installer)
        self.assertIn('web/multiplayer.js', installer)
        self.assertIn('services/emulatorjs_netplay', installer)
        self.assertIn('emulatorjs-netplay-server-linux-arm64', installer)


if __name__ == "__main__":
    unittest.main()
