(function () {
  'use strict';

  const MODE_KEY = 'lanBatoceraMultiplayerMode';
  const POLL_INTERVAL_MS = 2000;

  function storedMode() {
    try {
      return localStorage.getItem(MODE_KEY) || 'host';
    } catch {
      return 'host';
    }
  }

  function saveMode(mode) {
    if (!['host', 'join', 'off'].includes(mode)) {
      throw new Error('Invalid multiplayer mode.');
    }
    try {
      localStorage.setItem(MODE_KEY, mode);
    } catch {}
  }

  function gameLaunchUrl(game) {
    const query = new URLSearchParams({
      core: game.core,
      path: game.path,
      name: game.name,
      launch: Date.now().toString(),
    });
    return `/play.html?${query}`;
  }

  async function hostGame(game) {
    const response = await fetch('/api/multiplayer/host', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({game: {core: game.core, path: game.path, name: game.name, origin: location.origin}}),
    });
    const session = await response.json();
    if (!response.ok) {
      throw new Error(session.error || 'Could not create the multiplayer room.');
    }
    const url = new URL(gameLaunchUrl(game), location.origin);
    url.searchParams.set('multiplayer', 'host');
    url.searchParams.set('session', session.id);
    url.searchParams.set('token', session.token);
    return url.toString();
  }

  async function launch(game) {
    const mode = storedMode();
    if (mode === 'join') {
      throw new Error('This device is waiting for the host. Change Multiplayer Settings to Host or Off to choose a game.');
    }
    return mode === 'host' ? hostGame(game) : gameLaunchUrl(game);
  }

  function joinUrl(session) {
    const url = new URL(gameLaunchUrl(session.game), session.game.origin || location.origin);
    url.searchParams.set('multiplayer', 'join');
    url.searchParams.set('session', session.id);
    return url.toString();
  }

  function bindLibrary(elements) {
    const {openButton, dialog, closeButton, choices, status} = elements;
    let pollTimer;

    function renderMode(mode) {
      choices.forEach(button => button.classList.toggle('active', button.dataset.multiplayerMode === mode));
      openButton.textContent = mode === 'join' ? 'Ⅱ Join Mode' : mode === 'host' ? 'Ⅰ Host Mode' : '♙ Solo Mode';
      status.textContent = mode === 'join'
        ? 'Waiting for a host to start a game…'
        : mode === 'host'
          ? 'Games you start will create a two-player room. You are Player 1.'
          : 'Multiplayer is disabled. Games start normally.';
    }

    async function pollHost() {
      if (storedMode() !== 'join') return;
      try {
        const response = await fetch('/api/multiplayer/session', {cache: 'no-store'});
        const session = await response.json();
        if (session.active) {
          status.textContent = `Joining ${session.game.name} as Player 2…`;
          location.replace(joinUrl(session));
        }
      } catch {
        status.textContent = 'Host discovery is temporarily unavailable. Retrying…';
      }
    }

    function schedulePolling() {
      clearInterval(pollTimer);
      if (storedMode() === 'join') {
        pollHost();
        pollTimer = setInterval(pollHost, POLL_INTERVAL_MS);
      }
    }

    openButton.onclick = () => dialog.showModal();
    closeButton.onclick = () => dialog.close();
    choices.forEach(button => {
      button.onclick = () => {
        saveMode(button.dataset.multiplayerMode);
        renderMode(storedMode());
        schedulePolling();
      };
    });
    renderMode(storedMode());
    schedulePolling();
  }

  window.LanMultiplayer = {bindLibrary, launch, storedMode};
}());
