(() => {
  'use strict';

  const COMMON_BINDINGS = Object.freeze({
    2: { value: 'v', value2: 'SELECT' },
    3: { value: 'enter', value2: 'START' },
    4: { value: 'up arrow', value2: 'DPAD_UP' },
    5: { value: 'down arrow', value2: 'DPAD_DOWN' },
    6: { value: 'left arrow', value2: 'DPAD_LEFT' },
    7: { value: 'right arrow', value2: 'DPAD_RIGHT' },
    10: { value: 'q', value2: 'LEFT_TOP_SHOULDER' },
    11: { value: 'e', value2: 'RIGHT_TOP_SHOULDER' },
    12: { value: 'tab', value2: 'LEFT_BOTTOM_SHOULDER' },
    13: { value: 'r', value2: 'RIGHT_BOTTOM_SHOULDER' },
    14: { value: '', value2: 'LEFT_STICK' },
    15: { value: '', value2: 'RIGHT_STICK' },
    16: { value: '', value2: 'LEFT_STICK_X:+1' },
    17: { value: '', value2: 'LEFT_STICK_X:-1' },
    18: { value: '', value2: 'LEFT_STICK_Y:+1' },
    19: { value: '', value2: 'LEFT_STICK_Y:-1' },
    20: { value: '', value2: 'RIGHT_STICK_X:+1' },
    21: { value: '', value2: 'RIGHT_STICK_X:-1' },
    22: { value: '', value2: 'RIGHT_STICK_Y:+1' },
    23: { value: '', value2: 'RIGHT_STICK_Y:-1' }
  });

  const KEYBOARD_FACE_BUTTONS = Object.freeze({
    0: 'x',
    1: 's',
    8: 'z',
    9: 'a'
  });

  function createPlayerControls(faceButtons) {
    const controls = {};
    for (const [input, binding] of Object.entries(COMMON_BINDINGS)) {
      controls[input] = { ...binding };
    }
    for (const [input, gamepadButton] of Object.entries(faceButtons)) {
      controls[input] = {
        value: KEYBOARD_FACE_BUTTONS[input],
        value2: gamepadButton
      };
    }
    return controls;
  }

  function createPreset(id, label, faceButtons) {
    return Object.freeze({
      id,
      label,
      controls: Object.freeze({
        0: createPlayerControls(faceButtons),
        1: {},
        2: {},
        3: {}
      })
    });
  }

  const STANDARD_FACE_BUTTONS = Object.freeze({
    0: 'BUTTON_2',
    1: 'BUTTON_4',
    8: 'BUTTON_1',
    9: 'BUTTON_3'
  });

  const SWITCH_FACE_BUTTONS = Object.freeze({
    0: 'BUTTON_1',
    1: 'BUTTON_3',
    8: 'BUTTON_2',
    9: 'BUTTON_4'
  });

  const presets = Object.freeze({
    xbox: createPreset('xbox', 'Xbox Controller', STANDARD_FACE_BUTTONS),
    playstation: createPreset('playstation', 'PlayStation Controller', STANDARD_FACE_BUTTONS),
    switch: createPreset('switch', 'Switch Controller', SWITCH_FACE_BUTTONS)
  });

  function getPreset(presetId) {
    return presets[presetId] || null;
  }

  function connectedGamepads(gamepadProvider = navigator.getGamepads?.bind(navigator)) {
    if (!gamepadProvider) {
      return [];
    }
    try {
      return Array.from(gamepadProvider() || []).filter(Boolean);
    } catch {
      return [];
    }
  }

  window.LanControllerPresets = Object.freeze({
    connectedGamepads,
    getPreset,
    presets
  });
})();
