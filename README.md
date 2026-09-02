# LAN Batocera

Current release: **v1.6.1**. Releases follow Semantic Versioning; contribution
and release requirements are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

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

## Default sign-in information

These are three separate sign-in systems. Usernames and passwords are
case-sensitive.

| Access method | Address | Default username | Default password |
| --- | --- | --- | --- |
| Batocera SSH | `ssh root@batocera.local` | `root` | `linux` |
| LAN Batocera web file manager | `http://batoceraroms.local:8081` | `Batocera` | `Batocera` |
| Batocera Windows/SMB share | `\\BATOCERA\\share` | Guest access by default | No password by default |

Batocera's **Enforce Security** setting changes the SSH/root password to the
password shown or configured under **Main Menu → System Settings → Security**.
When it is enabled, Windows/SMB also uses username `root` and that same current
root password. It does not use the LAN web file manager's `Batocera` /
`Batocera` account. Some Windows organization policies block guest SMB access;
in that situation, enable Batocera's **Enforce Security** and sign in to the
Windows prompt as `root` with the current Batocera root password.

Change the LAN web file-manager credentials after the first login. Keep SSH,
SMB, ports 8080 and 8081 restricted to a trusted local network.
Both services live in Batocera's persistent `/userdata` partition and start with
Batocera's supported user-service system. The library provides console tiles
with game counts, console and handheld categories, system filtering, title
search, per-browser favorites and recently played history, and returns to the
library after EmulatorJS completes its exit and save cleanup. The responsive UI
uses phone-sized touch targets and bottom navigation, desktop keyboard shortcuts,
incremental card rendering, and automatic mobile/desktop EmulatorJS controls.
Desktop browsers default to EmulatorJS's **2xScaleHQ** GPU shader for a cleaner
scaled image. Phones default to native filtering to protect battery life and
frame rate. During play, open EmulatorJS's gear menu and change **Shader** to
Disabled, 2xScaleHQ, or 4xScaleHQ according to the client device's GPU. This
filters the locally rendered frame; it does not add detail to original ROM
textures or make the Raspberry Pi perform the emulation.
Game cells use an artwork-first layout when cover art is available: the cover
occupies most of the card, with system and title metadata arranged beneath it.
Cards without artwork retain a compact text layout, and phone layouts enlarge a
single-column cover further on narrow screens.

### Experimental multiplayer

Open **Multiplayer Settings** in the library and choose one mode:

- **Host · Player 1** names a LAN lobby and creates it when this device launches
  a game. The host retains restart, pause, save, and exit control.
- **Join · Player 2** or **Join · Player 3** lists the open lobbies on this
  Batocera device. Choose a lobby to open the host's exact game in the selected
  controller slot. Player 3 becomes available after Player 2 joins.
- **Solo** disables multiplayer and launches games normally.

Each browser runs the same emulation and EmulatorJS netplay synchronizes the
game state and inputs. This is not video mirroring: every player gets the same
game view without sending a video stream across the LAN, while each phone or PC
keeps its own assigned controls. The discovery layer preserves the host's exact
LAN origin so all browsers use the same room domain even when the device is
reachable by both IP address and `.local` name. Host sessions and disconnected
guest slots expire after 20 seconds without a heartbeat.
Every configured LAN Batocera system exposes the feature, but EmulatorJS netplay
is experimental and individual cores must be verified with real browsers. A
game and its emulator core must support three players before Player 3 can be
used.
Synchronization uses a Pi-local ARM64 build of the Apache-licensed EmulatorJS
netplay server on TCP port 4000. It is pinned to upstream commit
`4090ca7bda795a8b7a7596f4d41a4605b515d9c5`; the reproducible GitHub Actions
workflow builds the static binary and records the upstream license. Game data
comes directly from Batocera, and emulation runs locally in each browser.

Sega 32X libraries are scanned from `/userdata/roms/sega32x` and launched with
EmulatorJS's PicoDrive-backed `sega32x` core. ZIP and 7z containers are supported
alongside raw `.32x`, `.smd`, `.bin`, and `.md` ROMs.

Select **Get Artwork** in the LAN library to fetch missing box art for one
console. Start with the 10-game test, then choose the next 100 or all remaining
games. The job runs sequentially to protect Pi 3 memory, displays live progress,
can be cancelled, and never replaces existing artwork. Successful matches are
stored in that console's `images` directory and written to its `gamelist.xml`,
so they are available in both LAN Batocera and Batocera's HDMI interface. The
first metadata change creates a `gamelist.xml.lan-batocera.bak` backup.
The LAN library reads each entry's `<name>` and `<image>` fields, so proper game
titles and cover art created by Batocera's scraper or LAN Batocera's artwork
fetcher appear through the same interface. ROM filenames remain the fallback
when an entry has no display name.
If EmulationStation is already open on HDMI, use **Main Menu → Game Settings →
Update Games Lists** after the fetch finishes; the web feature does not restart
EmulationStation or interrupt someone using the television.

Artwork matching uses the ROM filename and the public Libretro Thumbnails
No-Intro naming catalog. Unusual dumps, hacks, translations, and filenames that
do not resemble catalog names may remain unmatched. The feature deliberately
does not guess among ambiguous results or overwrite metadata supplied by another
scraper.

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

From Windows PowerShell, the included version-pinned installer connects to the
device, prompts for its current SSH password, installs the release, and restarts
the LAN services:

```powershell
.\install-over-ssh.ps1 192.168.x.x
```

From macOS or Linux:

```bash
chmod +x install-over-ssh.sh
./install-over-ssh.sh 192.168.x.x
```

Replace `192.168.x.x` with the device address, or omit it when
`batocera.local` resolves. Neither helper stores a password. They work on both
the Raspberry Pi 3 B+ and CM4 Batocera targets because both use the same
64-bit ARM release payload.

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

For an existing Batocera installation, the version-pinned standalone LAN
feature installer downloads and runs the same reviewed release without requiring
a manual repository checkout. It adds LAN Batocera; it does not install,
replace, or re-image the Batocera operating system:

```bash
curl -fL https://raw.githubusercontent.com/HDR-Performance/lan-batocera/v1.6.1/standalone-install.sh -o /tmp/lan-batocera-install.sh
less /tmp/lan-batocera-install.sh
chmod +x /tmp/lan-batocera-install.sh
/tmp/lan-batocera-install.sh
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
queue accepts a complete folder containing up to 10,000 files while preserving
its nested directory structure;
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
the Batocera device over the LAN. Controllers connect to the browser device.
Every supported LAN console exposes **Save / Load** in the in-game menu and uses
the same saved-state manager, including manual saves, automatic screen-off
saves, previews, loading, portable downloads, local-file import, and
multi-download or multi-delete. One state downloads as a `.state` file;
multiple selected states download as a ZIP with a manifest. **Import & Load
State** accepts a local `.state` file from desktop and mobile file pickers,
stores it for the active game, and loads it immediately. Compatible libretro systems also
mirror saves into Batocera's native numbered state slots. N64 and C64 remain
browser-only because this Pi's Batocera defaults use different emulator cores;
copying those state files into native slots would label incompatible data as a
working Batocera save.

Commodore 64 games are scanned from `/userdata/roms/c64` and use EmulatorJS's
cycle-accurate `c64` core. Supported files match Batocera's C64 set: `.d64`,
`.d81`, `.crt`, `.prg`, `.tap`, `.t64`, `.m3u`, `.zip`, and `.7z`.
N64 and C64 launches bypass EmulatorJS's internal ROM/core cache and use a
size-and-modification revision in the ROM URL. Replacing a ROM at the same path
therefore downloads the new file without changing its save-state identity.
These systems also default to native video; mobile N64 uses the legacy core for
broader WebGL compatibility. N64 and C64 also ignore stale EmulatorJS settings.
Desktop browsers start games automatically. Mobile browsers receive one clearly
named **Start** button because mobile Safari and other phone browsers require a
fresh interaction before emulator audio and execution can begin; this avoids
the frozen auto-start and `undefined` resume screen that previously required
using EmulatorJS's Restart command.

On touch devices, EmulatorJS's toolbar-level Restart control is removed from
the gameplay surface so rapid face-button presses cannot trigger a stray reset.
A deliberate **Restart Game** action remains in LAN Batocera's mobile menu and
requires confirmation before discarding unsaved progress.

The **Controllers** menu provides pre-mapped Xbox, PlayStation, and Nintendo
Switch layouts. A selection is saved in that browser and applied before
EmulatorJS starts. On phones, **Touch / Browser Default** keeps EmulatorJS's
virtual touch gamepad enabled. A Bluetooth controller paired to the phone can
use any preset; some mobile browsers expose it only after a button is pressed,
so the manual selector remains available even when automatic detection reports
no controller. EmulatorJS's in-game controller settings remain available for
unusual or third-party pads.

All three physical-controller presets include both stick clicks and the complete
left/right analog-axis map used by N64 and other analog systems. Touch mode gives
the N64 stick a larger movement target. Choose **Move / Resize Touch Controls**
from the in-game controller menu to tap and drag the top, bottom, left, or right
control group. The selected group can be resized from 70% to 150%. Portrait and
landscape layouts are stored separately in that browser, and **Reset Layout**
restores the current orientation without changing the other one.

When a physical controller is already connected as a game starts, LAN Batocera
reconciles it with EmulatorJS after initialization and assigns it to Player 1.
This avoids a controller-detection race that could leave N64 analog sticks
unresponsive even though an Xbox, PlayStation, or Switch preset was selected.

The game page includes a large **Fullscreen** button with safe-area spacing for
phone screens. Fullscreen must be started from that tap because browsers require
direct user interaction. The button changes to **Exit Fullscreen** while active.
If an iPhone browser does not expose webpage fullscreen, the page explains how
to use **Share → Add to Home Screen** for an app-style view instead of falsely
claiming fullscreen was enabled.

When a phone locks, switches apps, or backgrounds the browser, LAN Batocera
immediately pauses the emulator and attempts one rolling **Automatic screen-off
save**. Returning to the page opens a pause menu and requires a tap on **Resume
Game**, which also gives mobile browsers the interaction needed to restore game
audio. The pause menu reports whether the autosave completed; mobile operating
systems may freeze JavaScript or networking before an asynchronous save can
finish. The newest successful automatic save replaces the previous automatic
save while manual saves remain untouched.

Select **Keep Screen On** once after starting a game to prevent supported phones
from dimming or sleeping. LAN Batocera first uses the browser-standard Screen
Wake Lock API. Because wake lock normally requires HTTPS and this project is a
local HTTP service, it also loads the MIT-licensed NoSleep.js compatibility
fallback. The lock is released whenever the game is paused or backgrounded and
is requested again from the player's **Resume Game** tap. Battery saver, low
battery, browser policy, or operating-system policy can still deny the request.

The default **Neon Arcade** theme is joined by Classic Dark and Pixel Purple.
The **Themes** menu also includes a validated eight-color custom theme builder.
Theme choices are stored per browser and do not alter Batocera's HDMI theme.
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
