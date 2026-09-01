(() => {
  'use strict';

  function bind({ canPause, pause, save, showPauseMenu }) {
    if (![canPause, pause, save, showPauseMenu].every(callback => typeof callback === 'function')) {
      return null;
    }

    let pausePending = false;
    let saveStatus = 'pending';

    const notifyVisiblePage = () => {
      if (pausePending && document.visibilityState === 'visible') {
        showPauseMenu(saveStatus);
      }
    };

    const pauseForBackground = () => {
      if (pausePending || !canPause()) {
        return;
      }
      pausePending = true;
      saveStatus = 'pending';
      pause();
      Promise.resolve(save())
        .then(() => {
          saveStatus = 'saved';
          notifyVisiblePage();
        })
        .catch(() => {
          saveStatus = 'failed';
          notifyVisiblePage();
        });
    };

    const handleVisibility = () => {
      if (document.visibilityState === 'hidden') {
        pauseForBackground();
        return;
      }
      notifyVisiblePage();
    };

    document.addEventListener('visibilitychange', handleVisibility, { capture: true });
    document.addEventListener('freeze', pauseForBackground, { capture: true });
    window.addEventListener('pagehide', pauseForBackground, { capture: true });
    window.addEventListener('pageshow', notifyVisiblePage, { capture: true });

    return Object.freeze({
      resume() {
        pausePending = false;
        saveStatus = 'pending';
      }
    });
  }

  window.LanMobileLifecycle = Object.freeze({ bind });
})();
