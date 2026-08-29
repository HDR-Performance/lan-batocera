# Batocera LAN Arcade

Batocera LAN Arcade adds two local-network web services to a Batocera device:

- A browser-playable ROM library at `http://BATOCERA-IP:8080`
- An authenticated drag-and-drop manager at `http://BATOCERA-IP:8081`

The arcade uses [EmulatorJS](https://emulatorjs.org/) in the client browser. The
file manager uses [FileBrowser Quantum](https://github.com/gtsteffaniak/filebrowser).
Both services live in Batocera's persistent `/userdata` partition and start with
Batocera's supported user-service system. The library provides console tiles
with game counts, console and handheld categories, system filtering, title
search, per-browser favorites and recently played history, and returns to the
library after EmulatorJS completes its exit and save cleanup. The responsive UI
uses phone-sized touch targets and bottom navigation, desktop keyboard shortcuts,
incremental card rendering, and automatic mobile/desktop EmulatorJS controls.

## Supported hardware

The installer targets Batocera v38 or newer on 64-bit ARM (`aarch64`), including
the Raspberry Pi 3 B+. The arcade server itself is lightweight because the web
browser performs the emulation.

## Install

Download or clone this repository on another computer, then copy it to Batocera:

```bash
scp -r batocera-lan-arcade root@BATOCERA-IP:/userdata/system/
ssh root@BATOCERA-IP
cd /userdata/system/batocera-lan-arcade
./install.sh
```

Batocera's default SSH login is `root` / `linux` when security has not been
enabled. The file manager's first login is `Batocera` / `Batocera`. Change both
from the account settings immediately after signing in; later restarts preserve
the changed credentials.

After installation:

- Open `http://BATOCERA-IP:8080` to play.
- Open `http://BATOCERA-IP:8081` to upload and manage files.
- Upload ROMs inside the correct directory under **Games**, such as `gba`, `nes`,
  `snes`, or `megadrive`.

The file manager accepts multi-file selection and drag-and-drop, runs up to three
uploads concurrently, and uses 50 MB chunks for large transfers. The browser
queue is uncapped and is intended to accept batches of up to 5,000 files;
transfers beyond the three active slots wait in the browser. ROM search indexing
is disabled to prevent large uploads from saturating low-memory Pi hardware while
ordinary folder browsing remains available. A local upload guard rejects
individual files larger than 1 GiB before they reach FileBrowser. Login sessions
remain valid for seven days so the default two-hour token expiration cannot
interrupt a long bulk upload.
Available storage, browser memory, browser limits, and network reliability remain
additional practical limits.

## Security boundary

The file manager deliberately exposes only these persistent data areas:

- `/userdata/roms`
- `/userdata/bios`
- `/userdata/saves`
- `/userdata/screenshots`

It does not expose `/`, `/boot`, or `/userdata/system`. The service uses password
authentication and binds to the LAN. Its initial password is intentionally easy
to enter, so change it immediately. Do not forward ports 8080 or 8081 through
your router. HTTP traffic is not encrypted, so use it only on a trusted local
network.

## ROMs and BIOS files

No copyrighted games or BIOS files are included. Use homebrew, public-domain, or
properly dumped content that you are legally permitted to use.

## Browser notes

The current arcade loads the stable EmulatorJS engine from its public CDN, so the
client browser needs internet access when starting a game. ROM data is served by
the Batocera device over the LAN. Controllers connect to the browser device, and
browser saves are separate from Batocera's native emulator saves.

## Remove

```bash
cd /userdata/system/batocera-lan-arcade
./uninstall.sh
```

The uninstaller removes the two services and their application files. It never
removes ROMs, BIOS files, saves, screenshots, or the FileBrowser database unless
you explicitly delete those files yourself.

## License

The project-specific code is available under the [MIT License](LICENSE).
EmulatorJS and FileBrowser Quantum remain under their respective licenses and are
not redistributed by this repository.
