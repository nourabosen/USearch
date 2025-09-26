# USearch — Ulauncher extension

**Find files quickly using the system locate database (plocate/locate) and include mounted hardware drives by performing a live scan.**

This fork combines the speed of `plocate` with a fallback live-search for mounted media, so external drives under `/run/media`, `/media`, or `/mnt` are discoverable even if the locate database excludes them.

## Features
- Fast indexed search using `plocate` or `locate`.
- Automatic live scanning of mounted hardware (`/run/media`, `/media`, `/mnt`) using `find`.
- Merges and de-duplicates results (plocate results appear first).
- Paginated result pages in Ulauncher — arrow keys navigate to the **More results** item to load the next page.
- Supports raw locate mode: `r <locate-args>` (e.g., `s r -S .png`).
- `Alt+Enter` on a result carries the full result list (same as previous behavior).
- Configurable results-per-page via Ulauncher preferences (`limit`).

## Usage
- Trigger: Type the configured keyword (default `s`) then your query.

Examples:
- `s davinci.png` — fast indexed search (plocate).
- `s hw photo.jpg` — live scan on mounted media (searches `/run/media`, `/media`, `/mnt`).
- `s r -S .png` — raw locate/plocate arguments (advanced).

Navigation:
- Use Up/Down arrows to move. Press Enter on a result to open it with the default system opener.
- The last item on a page will be `More results (...)` if additional pages exist — press Enter on it to load the next page.
- Alt+Enter on a result triggers the alternate action (copy full results).

## Installation
1. Ensure `plocate` or `locate` is installed:
   - Debian/Ubuntu (plocate): `sudo apt install plocate`
   - Fedora (plocate): `sudo dnf install plocate`
   - Or install `mlocate` if you prefer: `sudo apt install mlocate`

2. Make sure the locate database is present and up-to-date:
   ```bash
   sudo updatedb
