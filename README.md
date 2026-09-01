# LAN Batocera

LAN Batocera adds two local-network web services to a Batocera device:

- A browser-playable ROM library at <http://batocera.local:8080>
- An authenticated drag-and-drop manager at <http://batoceraroms.local:8081>

If a phone or computer does not support `.local` mDNS names, use the Batocera
device's current IPv4 address instead—for example,
`http://192.168.x.x:8080` and `http://192.168.x.x:8081`. `BATOCERA-IP` in older
instructions was a placeholder, not a literal hostname.

The arcade uses [EmulatorJS](https://emulatorjs.org/) in the client browser. The
file manager uses [FileBrowser Quantum](https://github.com/gtsteffaniak/filebrowser).
LAN Batocera also integrates with Batocera's supported service system and
`batocera-es-swissknife` emulator lifecycle commands. See
[Third-party notices](THIRD_PARTY_NOTICES.md) for upstream projects, authors,
licenses, and the exact integration boundaries.
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

- Open `http://batocera.local:8080` to play. The direct-IP address remains a
  fallback when a client does not support `.local` mDNS names.
- Open `http://batoceraroms.local:8081` to upload and manage files. LAN
  Batocera publishes this additional mDNS alias while its service is running.
- Upload ROMs inside the correct directory under **Games**, such as `gba`, `nes`,
  `snes`, or `megadrive`.
- Select **Refresh Games** in the arcade after adding ROMs to rescan supported
  system folders without restarting the service.

Both friendly names resolve to the same Batocera device, so their `:8080` and
`:8081` ports remain part of the URLs. DNS and mDNS names identify a host; web
browsers do not automatically select different HTTP ports from those names.

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

Upload jobs are displayed and started in top-to-bottom FIFO order with a hard
maximum of four active transfers. A transfer must make no progress for two minutes
before it is treated as stalled; a stall pauses the queue so later files do not
skip ahead. Completing a batch refreshes both the current directory listing and
the source storage-usage figures, including when failed items remain for review.

The desktop listing header includes **Type** alongside Name, Size, and Last
Modified. Selecting Type sorts folders and files by FileBrowser's MIME file-type
field and selecting it again reverses the order. This integration targets the
bundled FileBrowser Quantum v1.5.3 frontend and leaves unknown future frontend
assets unchanged instead of applying an unsafe partial patch.

The customized file-manager frontend suppresses FileBrowser Quantum's upstream
**An update is available** banner. LAN Batocera pins a tested upstream version;
updating the binary independently could invalidate its upload, sorting, storage,
and archive compatibility patches. Upstream attribution and license notices
remain available in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

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
LAN games run in the visiting phone or PC browser, not as emulator processes on
the Batocera host. When leaving a game, the page activates EmulatorJS's own
**Exit Emulation** control and waits for the documented `EJS_onExit` callback
or EmulatorJS's own exited state before releasing the emulator instance
and returning to the library. If closure is not confirmed, the page stays open
and reports the failure instead of claiming the game stopped.

After EmulatorJS reports that a newly selected game has started, LAN Batocera
performs one guarded restart through EmulatorJS's own **Restart** control. This
applies to every configured console core, including Nintendo 64 and Super
Nintendo, and cannot repeat in a loop during the same launch.

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
not redistributed by this repository. Batocera is an independent upstream
project. Full acknowledgements and license links are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
