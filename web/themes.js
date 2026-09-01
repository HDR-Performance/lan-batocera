(() => {
  'use strict';

  const THEME_STORAGE_KEY = 'lanBatoceraTheme';
  const CUSTOM_THEME_STORAGE_KEY = 'lanBatoceraCustomTheme';
  const COLOR_PATTERN = /^#[0-9a-f]{6}$/i;
  const COLOR_PROPERTIES = Object.freeze([
    'bg',
    'panel',
    'panel2',
    'line',
    'muted',
    'accent',
    'text',
    'gold'
  ]);

  const presets = Object.freeze({
    arcade: Object.freeze({
      id: 'arcade',
      name: 'Neon Arcade',
      colors: Object.freeze({
        bg: '#070511', panel: '#15102a', panel2: '#211542', line: '#533f78',
        muted: '#b7a9cf', accent: '#17f1d1', text: '#fff7ff', gold: '#ff4fd8'
      })
    }),
    classic: Object.freeze({
      id: 'classic',
      name: 'Classic Dark',
      colors: Object.freeze({
        bg: '#091018', panel: '#111e27', panel2: '#152832', line: '#29404c',
        muted: '#9eb1bc', accent: '#41d6c3', text: '#eef4f7', gold: '#ffd166'
      })
    }),
    pixel: Object.freeze({
      id: 'pixel',
      name: 'Pixel Purple',
      colors: Object.freeze({
        bg: '#10091c', panel: '#211333', panel2: '#32194b', line: '#613c7b',
        muted: '#c2a8d4', accent: '#b86cff', text: '#fff8ff', gold: '#55f6ff'
      })
    })
  });

  function sanitizeColors(colors) {
    const safeColors = {};
    for (const property of COLOR_PROPERTIES) {
      const value = String(colors?.[property] || '');
      if (!COLOR_PATTERN.test(value)) {
        return null;
      }
      safeColors[property] = value.toLowerCase();
    }
    return safeColors;
  }

  function readStorage(key) {
    try {
      return localStorage.getItem(key) || '';
    } catch {
      return '';
    }
  }

  function writeStorage(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      return false;
    }
    return true;
  }

  function customTheme() {
    try {
      const colors = sanitizeColors(JSON.parse(readStorage(CUSTOM_THEME_STORAGE_KEY)));
      return colors ? { id: 'custom', name: 'My Theme', colors } : null;
    } catch {
      return null;
    }
  }

  function getTheme(themeId) {
    if (themeId === 'custom') {
      return customTheme();
    }
    return presets[themeId] || null;
  }

  function applyTheme(theme) {
    if (!theme) {
      return false;
    }
    const colors = sanitizeColors(theme.colors);
    if (!colors) {
      return false;
    }
    for (const [property, value] of Object.entries(colors)) {
      document.documentElement.style.setProperty(`--${property}`, value);
    }
    document.documentElement.dataset.theme = theme.id;
    writeStorage(THEME_STORAGE_KEY, theme.id);
    return true;
  }

  function saveCustomTheme(colors) {
    const safeColors = sanitizeColors(colors);
    if (!safeColors) {
      return null;
    }
    if (!writeStorage(CUSTOM_THEME_STORAGE_KEY, JSON.stringify(safeColors))) {
      return null;
    }
    return { id: 'custom', name: 'My Theme', colors: safeColors };
  }

  function applySavedTheme() {
    const savedTheme = getTheme(readStorage(THEME_STORAGE_KEY));
    return applyTheme(savedTheme || presets.arcade);
  }

  window.LanBatoceraThemes = Object.freeze({
    applySavedTheme,
    applyTheme,
    colorProperties: COLOR_PROPERTIES,
    customTheme,
    getTheme,
    presets,
    saveCustomTheme
  });
})();
