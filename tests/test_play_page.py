import os
import unittest


PLAY_PAGE = os.path.join(os.path.dirname(__file__), "..", "web", "play.html")


class PlayPageTests(unittest.TestCase):
    def test_auto_starts_and_offers_save_or_skip_exit(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("window.EJS_startOnLoaded=!coarsePointer", page)
        self.assertIn("window.EJS_startButtonName='Start '+name", page)
        self.assertIn("Save State &amp; Exit", page)
        self.assertIn("Exit Without Saving", page)
        self.assertIn("button.ejs_menu_button", page)
        self.assertIn("==='Exit Emulation'", page)
        self.assertIn(".ejs_popup_container button", page)
        self.assertIn("confirmEmulatorExit", page)
        self.assertIn("EmulatorJS has exited", page)
        self.assertIn("The emulator did not confirm that it closed", page)
        self.assertIn("window.EJS_terminate?.()", page)
        self.assertIn("WEBGL_lose_context", page)
        self.assertIn("returnToLibrary()", page)
        self.assertIn("event.persisted", page)

    def test_saved_state_manager_supports_load_and_multi_delete(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("Choose a saved state", page)
        self.assertIn('id="stateOpen"', page)
        self.assertIn('id="saveState"', page)
        self.assertIn("The save-state request timed out. The game has been resumed.", page)
        self.assertIn('class="delete-choice" type="checkbox"', page)
        self.assertIn('class="load-choice" type="radio"', page)
        self.assertIn("/api/states/data", page)
        self.assertIn("method:'DELETE'", page)
        self.assertIn('id="importStateFile" type="file"', page)
        self.assertIn('id="downloadState"', page)
        self.assertIn('id="downloadStates"', page)
        self.assertIn("/api/states/export", page)
        self.assertIn("file.arrayBuffer()", page)
        self.assertIn("window.EJS_emulator.gameManager.loadState(bytes)", page)
        self.assertIn("MAX_IMPORTED_STATE_BYTES=64*1024*1024", page)

    def test_native_hdmi_game_blocks_loader(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("/api/session-status", page)
        self.assertIn("status.nativeGameRunning", page)
        self.assertIn("Console in use", page)
        self.assertIn("document.createElement('script')", page)
        self.assertIn("Stop HDMI Game &amp; Start LAN", page)
        self.assertIn("/api/session-stop", page)
        self.assertIn("X-LAN-Batocera-Action", page)

    def test_game_start_does_not_restart_a_partially_loaded_emulator(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("window.EJS_onGameStart=handleGameStart", page)
        self.assertIn("prepareStartedGame()", page)
        self.assertIn("if(gameStartHandled)return", page)
        self.assertNotIn("document.body.append(loader);prepareStartedGame()", page)
        self.assertNotIn("waitForMenuButton('Restart')", page)
        self.assertIn("if(!confirm('Restart this game from the beginning?", page)
        self.assertIn("restart.click()", page)
        self.assertNotIn("startupRestartState", page)

    def test_rom_revision_bypasses_stale_emulatorjs_cache(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("romRevision=p.get('revision')||''", page)
        self.assertIn("'?revision='+encodeURIComponent(romRevision)", page)
        self.assertIn("gameKey=core+':'+path", page)

        index_path = os.path.join(os.path.dirname(PLAY_PAGE), "index.html")
        with open(index_path, encoding="utf-8") as source:
            library_page = source.read()
        self.assertIn("game.revision||''", library_page)

    def test_desktop_defaults_to_hq_scaling_with_mobile_native_fallback(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn("coarsePointer||compatibilityCore?'disabled':'2xScaleHQ.glslp'", page)
        self.assertIn("core==='n64'||core==='c64'", page)
        self.assertIn("window.EJS_cacheConfig={enabled:!compatibilityCore", page)
        self.assertIn("window.EJS_disableLocalStorage=compatibilityCore", page)
        self.assertIn("window.EJS_forceLegacyCores=core==='n64'&&coarsePointer", page)
        self.assertIn("window.EJS_defaultOptions={shader:defaultShader}", page)
        self.assertIn("Video: 2× HQ", page)

    def test_phone_friendly_fullscreen_control_uses_browser_api(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn('id="fullscreen"', page)
        self.assertIn('aria-pressed="false"', page)
        self.assertIn('/fullscreen-controls.js', page)
        self.assertIn("LanFullscreenControls.bind", page)
        self.assertIn("env(safe-area-inset-bottom)", page)

    def test_mobile_game_controls_collapse_into_one_touch_menu(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn('id="mobileToolsToggle"', page)
        self.assertIn('aria-controls="mobileToolsPanel"', page)
        self.assertIn("setMobileToolsOpen", page)
        self.assertIn("mobile-tools-panel.open", page)
        self.assertIn("overflow-y:auto", page)
        self.assertIn("overscroll-behavior:contain", page)
        self.assertIn("bottom:max(10px,env(safe-area-inset-bottom))", page)
        self.assertIn('id="restartGame"', page)
        self.assertIn("function protectMobileRestart()", page)
        self.assertIn("restart.hidden=true", page)
        self.assertIn("Restart this game from the beginning?", page)

    def test_screen_lock_pauses_autosaves_and_requires_resume(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn('/mobile-lifecycle.js', page)
        self.assertIn('Automatic screen-off save', page)
        self.assertIn('id="resumeModal"', page)
        self.assertIn('id="resumeGame"', page)
        self.assertIn('LanMobileLifecycle.bind', page)
        self.assertIn("window.EJS_emulator?.pause?.()", page)
        self.assertIn("RESUME_INPUT_RESET_DELAY_MS=80", page)
        self.assertIn("emulator.pause?.();await sleep(RESUME_INPUT_RESET_DELAY_MS);emulator.play?.()", page)
        self.assertIn("await recoverEmulatorInput()", page)
        self.assertIn("STATE_REQUEST_TIMEOUT_MS=15000", page)
        self.assertIn("function fetchStateApi", page)
        self.assertIn("showStateManager();try{const response=await fetchStateApi", page)
        self.assertIn("finally{stateModal.classList.remove('busy');await recoverEmulatorInput()}", page)

    def test_game_submenus_have_back_to_game_controls(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn('id="closeGameMenu"', page)
        self.assertIn('id="controllerBack"', page)
        self.assertIn('id="stateBack"', page)
        self.assertGreaterEqual(page.count("← Back to Game"), 4)

    def test_keep_screen_on_uses_wake_lock_with_versioned_fallback(self):
        with open(PLAY_PAGE, encoding="utf-8") as source:
            page = source.read()
        self.assertIn('id="wakeLock"', page)
        self.assertIn('/wake-lock.js', page)
        self.assertIn('nosleep.js@0.12.0', page)
        self.assertIn('integrity="sha256-', page)
        self.assertIn("wakeLockController?.disable()", page)
        self.assertIn("wakeLockController?.enable()", page)


if __name__ == "__main__":
    unittest.main()
