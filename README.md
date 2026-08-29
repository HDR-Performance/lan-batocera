# LAN Batocera

LAN Batocera adds two local-network web services to a Batocera device:

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
Sega 32X libraries are scanned from `/userdata/roms/sega32x` and launched with
EmulatorJS's PicoDrive-backed `sega32x` core. ZIP and 7z containers are supported
alongside raw `.32x`, `.smd`, `.bin`, and `.md` ROMs.

## Supported hardware

The installer targets Batocera v38 or newer on 64-bit ARM (`aarch64`), including
the Raspberry Pi 3 B+. The arcade server itself is lightweight because the web
browser performs the emulation.

## Install over SSH

Enable SSH in Batocera, find its LAN IP address, and connect from PowerShell or a
terminal. The default Batocera SSH login is `root` / `linux` when security has
not been enabled:

```bash
ssh root@BATOCERA-IP
```

On the Batocera SSH prompt, download and install the public project:

```bash
cd /userdata/system
curl -fL https://github.com/HDR-Performance/lan-batocera/archive/refs/heads/main.tar.gz -o /tmp/lan-batocera.tar.gz
test ! -e /userdata/system/lan-batocera || { echo "lan-batocera already exists; move or update it first"; exit 1; }
mkdir /userdata/system/lan-batocera
tar -xzf /tmp/lan-batocera.tar.gz -C /userdata/system/lan-batocera --strip-components=1
cd /userdata/system/lan-batocera
chmod +x install.sh uninstall.sh
./install.sh
```

The file manager's first login is `Batocera` / `Batocera`. Change both from the
account settings immediately after signing in; later restarts preserve the
changed credentials.

After installation:

- Open `http://BATOCERA-IP:8080` to play.
- Open `http://BATOCERA-IP:8081` to upload and manage files.
- Upload ROMs inside the correct directory under **Games**, such as `gba`, `nes`,
  `snes`, or `megadrive`.
- Select **Refresh Games** in the arcade after adding ROMs to rescan supported
  system folders without restarting the service.

The file manager accepts multi-file selection and drag-and-drop, runs up to four
uploads concurrently, and uses 50 MB chunks for large transfers. The browser
queue is uncapped and is intended to accept batches of up to 5,000 files;
transfers beyond the four active slots wait in the browser. ROM search indexing
is disabled to prevent large uploads from saturating low-memory Pi hardware while
ordinary folder browsing remains available. A local upload guard rejects
individual files larger than 1 GiB before they reach FileBrowser. Login sessions
remain valid for seven days so the default two-hour token expiration cannot
interrupt a long bulk upload.
Available storage, browser memory, browser limits, and network reliability remain
additional practical limits.

The desktop listing header includes **Type** alongside Name, Size, and Last
Modified. Selecting Type sorts folders and files by FileBrowser's MIME file-type
field and selecting it again reverses the order. This integration targets the
bundled FileBrowser Quantum v1.5.3 frontend and leaves unknown future frontend
assets unchanged instead of applying an unsafe partial patch.

Select **Auto Extract** in the file manager to open the archive tools and unpack an uploaded ZIP or RAR into Games
or BIOS. Extraction requires a valid file-manager login, refuses path traversal
and symbolic links, never overwrites an existing destination folder, limits an
archive to 50,000 entries and 10 GiB expanded size, and removes a partial output
folder if extraction fails. Refresh the arcade library after extracting ROMs.

The same Archive Tools page includes **Auto Extract Directory**. It scans one
selected Games or BIOS directory for ZIP and RAR files (not its subdirectories), handles
them sequentially to limit Pi memory and storage load, and places each archive's
contents directly beside that archive. An archive is deleted only after its complete
contents have been validated and moved successfully. Conflicting, corrupt, or
unsafe archives are kept and reported in the final results. Password-protected
and multi-volume RAR archives are retained and reported rather than partially
processed. 7z archives are not currently included in the batch operation.

When **Auto Extract** is selected while browsing a Games or BIOS folder, the
tools page reads that current FileBrowser location and starts the batch for it
immediately. The directory form remains available as a fallback when a browser
does not provide the current-page location.

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
After choosing a game, select its **Start** button once. This deliberate browser
interaction reliably unlocks WebAudio and the emulator core; automatic startup
is disabled because browsers can suspend a new page until it receives input.

## Remove

```bash
cd /userdata/system/lan-batocera
./uninstall.sh
```

The uninstaller removes the two services and their application files. It never
removes ROMs, BIOS files, saves, screenshots, or the FileBrowser database unless
you explicitly delete those files yourself.

## License

The project-specific code is available under the [MIT License](LICENSE).
EmulatorJS and FileBrowser Quantum remain under their respective licenses and are
not redistributed by this repository.
