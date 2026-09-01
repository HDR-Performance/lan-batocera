# Third-party notices and acknowledgements

LAN Batocera is an independent community project. It is not an official
Batocera, EmulatorJS, or FileBrowser Quantum product.

## Batocera Linux

- Project: [batocera-linux/batocera.linux](https://github.com/batocera-linux/batocera.linux)
- Credit: the Batocera Linux maintainers and contributors
- License/copyright terms: [Batocera COPYING](https://github.com/batocera-linux/batocera.linux/blob/master/COPYING)
- Use here: the installer targets Batocera's persistent `/userdata` layout and
  user-service system. Native emulator detection and graceful shutdown use the
  upstream `batocera-es-swissknife --emupid` and `--emukill` interfaces.

No Batocera source code, firmware, ROMs, BIOS files, or Batocera trademarks are
redistributed by this repository.

## EmulatorJS

- Project: [EmulatorJS/EmulatorJS](https://github.com/EmulatorJS/EmulatorJS)
- Credit: Ethan O'Brien (`@ethanaobrien`), Allan Niles (`@allancoding`), and
  the EmulatorJS contributors
- License: [GNU General Public License v3.0](https://github.com/EmulatorJS/EmulatorJS/blob/main/LICENSE)
- Use here: the LAN arcade configures the separately hosted EmulatorJS client
  from its public CDN. Game start, save-state, and confirmed exit behavior use
  EmulatorJS's public browser API and lifecycle callbacks.

EmulatorJS is not vendored or redistributed in this repository. A visiting
browser downloads it from the upstream CDN at runtime.

## EmulatorJS Netplay Server

- Project: [EmulatorJS/EmulatorJS-Netplay](https://github.com/EmulatorJS/EmulatorJS-Netplay)
- Credit: the EmulatorJS maintainers and netplay contributors
- License: [Apache License 2.0](https://github.com/EmulatorJS/EmulatorJS-Netplay/blob/rust/LICENSE)
- Use here: LAN Batocera builds the lightweight signaling and synchronization
  server for `aarch64-unknown-linux-musl` from upstream commit
  `4090ca7bda795a8b7a7596f4d41a4605b515d9c5`. The reproducible workflow stages
  the binary, exact commit identifier, and upstream license together.

The release binary is distributed without modification and runs as a separate
Batocera service on TCP port 4000. LAN Batocera's project-specific Host/Join UI
and active-game discovery remain MIT-licensed code from this repository.

## FileBrowser Quantum

- Project: [gtsteffaniak/filebrowser](https://github.com/gtsteffaniak/filebrowser)
- Credit: Graham Steffaniak (`@gtsteffaniak`), the original File Browser
  contributors, and the FileBrowser Quantum contributors
- License: [Apache License 2.0](https://github.com/gtsteffaniak/filebrowser/blob/main/LICENSE)
- Use here: the installer downloads the upstream ARM64 release binary. LAN
  Batocera supplies configuration, a restricted storage boundary, an upload
  proxy, and compatibility patches for the configured upstream version.

The FileBrowser Quantum binary is downloaded during installation and is not
stored in this repository.

## Libretro Thumbnails

- Project: [libretro-thumbnails](https://github.com/libretro-thumbnails/libretro-thumbnails)
- Credit: the Libretro project, thumbnail repository maintainers, and artwork
  contributors
- Use here: the optional **Get Artwork** action downloads matching box-art PNGs
  directly from system-specific Libretro thumbnail repositories at runtime.

LAN Batocera does not bundle or redistribute the thumbnail collections. Artwork
and game imagery may remain copyrighted by their respective rights holders;
users are responsible for ensuring their use is permitted in their jurisdiction.

## NoSleep.js

- Project: [richtr/NoSleep.js](https://github.com/richtr/NoSleep.js)
- Credit: Rich Tibbett and NoSleep.js contributors
- License: [MIT License](https://github.com/richtr/NoSleep.js/blob/master/LICENSE)
- Use here: version 0.12.0 is loaded from jsDelivr at runtime as a compatibility
  fallback when the standard Screen Wake Lock API is unavailable on LAN HTTP.

NoSleep.js is not vendored in this repository. A visiting browser downloads the
version-pinned distribution at runtime.

## Platform and standard-library components

The project uses Batocera's bundled Python 3 runtime and Python standard
library, POSIX shell utilities, and browser-standard HTML, CSS, and JavaScript.
Those components are not redistributed here beyond project-authored scripts.

## Project-specific code

Unless a file says otherwise, the project-specific source in this repository is
Copyright (c) 2026 HDR Performance and licensed under the repository's
[MIT License](LICENSE). Third-party project names identify compatibility and do
not imply endorsement.
