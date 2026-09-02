(function () {
  'use strict';

  const MODE_KEY = 'lanBatoceraMultiplayerMode';
  const LOBBY_NAME_KEY = 'lanBatoceraLobbyName';
  const DEFAULT_LOBBY_NAME = 'Player 1 Lobby';
  const POLL_INTERVAL_MS = 2000;
  const VALID_MODES = Object.freeze(['host', 'join2', 'join3', 'join4', 'off']);

  function readStorage(key, fallback = '') {
    try {
      return localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  }

  function writeStorage(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {}
  }

  function storedMode() {
    const mode = readStorage(MODE_KEY, 'off');
    return VALID_MODES.includes(mode) ? mode : 'off';
  }

  function saveMode(mode) {
    if (!VALID_MODES.includes(mode)) {
      throw new Error('Invalid multiplayer mode.');
    }
    writeStorage(MODE_KEY, mode);
  }

  function gameLaunchUrl(game) {
    const query = new URLSearchParams({
      core: game.core,
      path: game.path,
      name: game.name,
      revision: game.revision || '',
      launch: Date.now().toString(),
    });
    return `/play.html?${query}`;
  }

  async function hostGame(game) {
    const lobbyName = readStorage(LOBBY_NAME_KEY, DEFAULT_LOBBY_NAME).trim() ||
      DEFAULT_LOBBY_NAME;
    writeStorage(LOBBY_NAME_KEY, lobbyName);
    const response = await fetch('/api/multiplayer/host', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        game: {core: game.core, path: game.path, name: game.name,
          revision: game.revision || '', origin: location.origin},
        lobbyName,
        maxPlayers: 4,
      }),
    });
    const session = await response.json();
    if (!response.ok) {
      throw new Error(session.error || 'Could not create the multiplayer lobby.');
    }
    const url = new URL(gameLaunchUrl(game), location.origin);
    url.searchParams.set('multiplayer', 'host');
    url.searchParams.set('session', session.id);
    url.searchParams.set('token', session.token);
    url.searchParams.set('player', '1');
    url.searchParams.set('players', session.maxPlayers.toString());
    url.searchParams.set('lobby', session.lobbyName);
    return url.toString();
  }

  async function launch(game) {
    const mode = storedMode();
    if (mode.startsWith('join')) {
      throw new Error('This device is a guest. Open Multiplayer Settings and choose an available LAN lobby.');
    }
    return mode === 'host' ? hostGame(game) : gameLaunchUrl(game);
  }

  function joinUrl(session, player) {
    const url = new URL(gameLaunchUrl(session.game), session.game.origin || location.origin);
    url.searchParams.set('multiplayer', 'join');
    url.searchParams.set('session', session.id);
    url.searchParams.set('player', player.toString());
    url.searchParams.set('players', session.maxPlayers.toString());
    url.searchParams.set('lobby', session.lobbyName);
    return url.toString();
  }

  function bindLibrary(elements) {
    const {openButton, dialog, closeButton, choices, status, hostSetup,
      lobbyNameInput, lobbyList, refreshButton} = elements;
    let pollTimer;

    function selectedPlayer() {
      const mode = storedMode();
      if (mode === 'join4') return 4;
      return mode === 'join3' ? 3 : 2;
    }

    function renderMode(mode) {
      choices.forEach(button => button.classList.toggle(
        'active', button.dataset.multiplayerMode === mode));
      hostSetup.hidden = mode !== 'host';
      lobbyList.hidden = !mode.startsWith('join');
      refreshButton.hidden = !mode.startsWith('join');
      openButton.textContent = mode === 'host' ? 'Ⅰ Host Lobby' :
        mode === 'join2' ? 'Ⅱ Player 2' : mode === 'join3' ? 'Ⅲ Player 3' :
          mode === 'join4' ? 'Ⅳ Player 4' : '♙ Solo Mode';
      status.textContent = mode === 'host'
        ? 'Name the lobby, then choose a game. This device is Player 1.'
        : mode.startsWith('join')
          ? `Choose an open LAN lobby as Player ${selectedPlayer()}.`
          : 'Multiplayer is disabled. Games start normally.';
    }

    function canJoin(session, player) {
      if (player > session.maxPlayers || session.joinedPlayers.includes(player)) return false;
      return player === 2 || session.joinedPlayers.includes(player - 1);
    }

    async function joinLobby(session, player) {
      status.textContent = `Joining ${session.lobbyName} as Player ${player}…`;
      const response = await fetch('/api/multiplayer/join', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: session.id, player}),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Could not join that lobby.');
      location.replace(joinUrl(result, player));
    }

    async function refreshLobbies() {
      if (!storedMode().startsWith('join')) return;
      const player = selectedPlayer();
      try {
        const response = await fetch('/api/multiplayer/sessions', {cache: 'no-store'});
        if (!response.ok) throw new Error('Lobby discovery is unavailable.');
        const sessions = await response.json();
        lobbyList.replaceChildren();
        for (const session of sessions) {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'controller-choice lobby-choice';
          button.disabled = !canJoin(session, player);
          button.textContent = `${session.lobbyName} · ${session.game.name} · ${session.players}/${session.maxPlayers}`;
          button.onclick = () => joinLobby(session, player).catch(error => {
            status.textContent = error.message;
            refreshLobbies();
          });
          lobbyList.append(button);
        }
        if (!sessions.length) status.textContent = 'No open LAN lobbies found. Waiting for Player 1…';
      } catch (error) {
        status.textContent = `${error.message} Retrying…`;
      }
    }

    function schedulePolling() {
      clearInterval(pollTimer);
      if (storedMode().startsWith('join')) {
        refreshLobbies();
        pollTimer = setInterval(refreshLobbies, POLL_INTERVAL_MS);
      }
    }

    lobbyNameInput.value = readStorage(LOBBY_NAME_KEY, DEFAULT_LOBBY_NAME);
    lobbyNameInput.oninput = () => writeStorage(LOBBY_NAME_KEY, lobbyNameInput.value.trim());
    refreshButton.onclick = refreshLobbies;
    openButton.onclick = () => {
      dialog.showModal();
      refreshLobbies();
    };
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
