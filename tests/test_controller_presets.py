import os
import unittest


REPOSITORY_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


class ControllerPresetTests(unittest.TestCase):
    def read_file(self, relative_path):
        with open(os.path.join(REPOSITORY_ROOT, relative_path), encoding="utf-8") as source_file:
            return source_file.read()

    def test_three_named_controller_presets_are_available(self):
        presets = self.read_file("web/controller-presets.js")
        self.assertIn("Xbox Controller", presets)
        self.assertIn("PlayStation Controller", presets)
        self.assertIn("Switch Controller", presets)
        self.assertIn("SWITCH_FACE_BUTTONS", presets)

    def test_play_page_applies_controls_before_loading_emulator(self):
        play_page = self.read_file("web/play.html")
        preset_script_position = play_page.index('/controller-presets.js')
        loader_position = play_page.index("loader.src='https://cdn.emulatorjs.org")
        self.assertLess(preset_script_position, loader_position)
        self.assertIn("window.EJS_defaultControls=preset.controls", play_page)
        self.assertIn("prepareController()", play_page)

    def test_library_exposes_touch_and_bluetooth_guidance(self):
        library_page = self.read_file("web/index.html")
        self.assertIn("Touch / Browser Default", library_page)
        self.assertIn("Bluetooth", library_page)
        self.assertIn("Controllers", library_page)

    def test_in_game_menu_can_change_controller_mode(self):
        play_page = self.read_file("web/play.html")
        self.assertIn('id="controllerStatus"', play_page)
        self.assertIn("$('controllerStatus').onclick", play_page)
        self.assertIn("Touch Controls / Browser Default", play_page)

    def test_physical_controller_mode_hides_virtual_gamepad(self):
        play_page = self.read_file("web/play.html")
        self.assertIn(
            "body[data-controller-input=physical] .ejs_virtualGamepad_parent",
            play_page,
        )
        self.assertIn("toggleVirtualGamepad?.(isVisible)", play_page)
        self.assertIn("setTouchControlsVisible(false)", play_page)
        self.assertIn("setTouchControlsVisible(true)", play_page)

    def test_all_presets_include_documented_analog_stick_axes(self):
        presets = self.read_file("web/controller-presets.js")
        expected_axes = (
            "LEFT_STICK_X:+1",
            "LEFT_STICK_X:-1",
            "LEFT_STICK_Y:+1",
            "LEFT_STICK_Y:-1",
            "RIGHT_STICK_X:+1",
            "RIGHT_STICK_X:-1",
            "RIGHT_STICK_Y:+1",
            "RIGHT_STICK_Y:-1",
        )
        for axis in expected_axes:
            self.assertIn(axis, presets)
        self.assertIn("RIGHT_STICK", presets)

    def test_running_emulator_receives_preset_and_connected_gamepad(self):
        presets = self.read_file("web/controller-presets.js")
        play_page = self.read_file("web/play.html")
        self.assertIn("function synchronizeEmulator(emulator, preset)", presets)
        self.assertIn("emulator.defaultControllers = copyControls(controls)", presets)
        self.assertIn("emulator.controls = controls", presets)
        self.assertIn("emulator.gamepadSelection[playerIndex]", presets)
        self.assertIn("synchronizeControllerPreset(preset)", play_page)
        self.assertIn("addEventListener('gamepadconnected'", play_page)

    def test_touch_layout_editor_is_loaded_before_emulator(self):
        play_page = self.read_file("web/play.html")
        self.assertIn('/touch-layout.js', play_page)
        self.assertIn('id="customizeTouchLayout"', play_page)
        self.assertIn('id="touchLayoutScale"', play_page)
        self.assertIn("window.EJS_controlScheme=core", play_page)
        self.assertLess(
            play_page.index('/touch-layout.js'),
            play_page.index("loader.src='https://cdn.emulatorjs.org"),
        )

    def test_touch_layout_supports_drag_resize_and_orientation_storage(self):
        editor = self.read_file("web/touch-layout.js")
        self.assertIn("lanBatoceraTouchLayoutV1", editor)
        self.assertIn("orientationKey()", editor)
        self.assertIn("handlePointerDown", editor)
        self.assertIn("handlePointerMove", editor)
        self.assertIn("setSelectedScale", editor)
        self.assertIn("Reset Layout", self.read_file("web/play.html"))


if __name__ == "__main__":
    unittest.main()
