(() => {
  'use strict';

  function bind(button, status) {
    if (!button || !status) {
      return null;
    }

    let active = false;
    let nativeLock = null;
    let fallbackLock = null;

    const render = message => {
      button.textContent = active ? '☀ Screen Awake' : '☾ Keep Screen On';
      button.setAttribute('aria-pressed', String(active));
      status.textContent = message || '';
    };

    const disable = async () => {
      active = false;
      if (nativeLock && !nativeLock.released) {
        await nativeLock.release().catch(() => {});
      }
      nativeLock = null;
      fallbackLock?.disable?.();
      fallbackLock = null;
      render('');
    };

    const enable = async () => {
      if (active) {
        return true;
      }
      if (navigator.wakeLock && window.isSecureContext) {
        try {
          nativeLock = await navigator.wakeLock.request('screen');
          active = true;
          nativeLock.addEventListener('release', () => {
            active = false;
            nativeLock = null;
            render('Screen-awake mode was released by the phone.');
          }, { once: true });
          render('Screen will stay awake while the game is active.');
          return true;
        } catch {
          nativeLock = null;
        }
      }
      if (typeof window.NoSleep === 'function') {
        try {
          fallbackLock = new window.NoSleep();
          await fallbackLock.enable();
          active = true;
          render('Compatibility screen-awake mode is active.');
          return true;
        } catch {
          fallbackLock = null;
        }
      }
      render('This browser blocked screen-awake mode. Check battery saver settings or keep the phone connected to power.');
      return false;
    };

    button.addEventListener('click', () => {
      if (active) {
        disable();
        return;
      }
      enable();
    });
    render('Tap once to prevent dimming while you play.');

    return Object.freeze({ disable, enable });
  }

  window.LanWakeLock = Object.freeze({ bind });
})();
