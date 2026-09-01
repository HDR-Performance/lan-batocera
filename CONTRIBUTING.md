# Contributing to LAN Batocera

## Versioning

LAN Batocera follows [Semantic Versioning](https://semver.org/):

- `MAJOR` changes when compatibility is intentionally broken.
- `MINOR` changes when a backward-compatible feature is added.
- `PATCH` changes when backward-compatible behavior is corrected.

Every release commit must update `VERSION`, use a commit subject beginning with
`release: vMAJOR.MINOR.PATCH`, and receive the matching annotated Git tag. A
version must never move backward or be reused for different source.

## Code standards

- Python uses four spaces, snake_case names, type hints, guard clauses, and
  named constants for operational limits.
- JavaScript and CSS use two spaces and semantic camelCase names.
- Functions have one responsibility and repeated behavior belongs in helpers.
- Validate external input before filesystem, subprocess, or network access.
- Keep comments limited to design intent that the code cannot express itself.
- Remove temporary diagnostics and commented-out code before committing.

Run the complete validation suite before opening a change:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile src/server.py src/upload_proxy.py
```
