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

## Platform and standard-library components

The project uses Batocera's bundled Python 3 runtime and Python standard
library, POSIX shell utilities, and browser-standard HTML, CSS, and JavaScript.
Those components are not redistributed here beyond project-authored scripts.

## Project-specific code

Unless a file says otherwise, the project-specific source in this repository is
Copyright (c) 2026 HDR Performance and licensed under the repository's
[MIT License](LICENSE). Third-party project names identify compatibility and do
not imply endorsement.
