(() => {
  'use strict';

  function activeFullscreenElement() {
    return document.fullscreenElement || document.webkitFullscreenElement || null;
  }

  function requestFullscreen(target) {
    const request = target.requestFullscreen
      || target.webkitRequestFullscreen
      || target.webkitRequestFullScreen;
    if (!request) {
      return null;
    }
    return Promise.resolve(request.call(target));
  }

  function exitFullscreen() {
    const exit = document.exitFullscreen
      || document.webkitExitFullscreen
      || document.webkitCancelFullScreen;
    if (!exit) {
      return null;
    }
    return Promise.resolve(exit.call(document));
  }

  function updateButton(button) {
    const isFullscreen = Boolean(activeFullscreenElement());
    button.textContent = isFullscreen ? '↙ Exit Fullscreen' : '⛶ Fullscreen';
    button.setAttribute('aria-pressed', String(isFullscreen));
  }

  function bind(button, status, target = document.documentElement) {
    if (!button || !status || !target) {
      return false;
    }

    const showUnsupportedMessage = () => {
      status.textContent = 'This browser cannot enter webpage fullscreen. On iPhone, use Share → Add to Home Screen for an app-style view.';
    };

    button.addEventListener('click', async () => {
      status.textContent = '';
      try {
        const action = activeFullscreenElement() ? exitFullscreen() : requestFullscreen(target);
        if (!action) {
          showUnsupportedMessage();
          return;
        }
        await action;
      } catch {
        status.textContent = 'Fullscreen was blocked. Tap the button again after interacting with the page.';
      }
    });

    const handleChange = () => {
      updateButton(button);
      status.textContent = activeFullscreenElement() ? 'Fullscreen enabled.' : '';
    };
    document.addEventListener('fullscreenchange', handleChange);
    document.addEventListener('webkitfullscreenchange', handleChange);
    updateButton(button);
    return true;
  }

  window.LanFullscreenControls = Object.freeze({ bind });
})();
