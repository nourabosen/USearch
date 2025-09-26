# USearch — Ulauncher Extension

**Find files quickly using the system locate database (plocate/locate) and include mounted hardware drives by performing a live scan.**

This fork combines the speed of `plocate` with a fallback live-search for mounted media, allowing external drives under `/run/media`, `/media`, or `/mnt` to be discoverable even if the locate database excludes them.

## Features
- Fast indexed search using `plocate` or `locate`.
- Automatic live scanning of mounted hardware (`/run/media`, `/media`, `/mnt`) using `find`.
- Merges and de-duplicates results (plocate results appear first).
- Paginated result pages in Ulauncher — arrow keys navigate to the **More results** item to load the next page.
- Supports raw locate mode: `r <locate-args>` (e.g., `s r -S .png`).
- `Alt+Enter` on a result carries the full result list (same as previous behaviour).
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
   ```
   On systems with `plocate`, enable/update the timer:
   ```bash
   sudo systemctl enable --now plocate-updatedb.timer
   ```

3. Install the extension via Ulauncher (copy this repo into your Ulauncher extensions folder or use the extension manager if you publish it).

## Notes

* The extension does two searches: an indexed `plocate/locate` query (fast) and a live `find` on configured hardware paths (slower). Combined queries may be slower when mounted drives are large.
* If you prefer system indexing to include your external drives automatically, edit `/etc/updatedb.conf` and remove `/run` and `/media` from `PRUNEPATHS`, then run `sudo updatedb`.
* The "live find" is limited to the folders: `/run/media`, `/media`, and `/mnt`. You can update `locator.hardware_paths` in `locator.py` to include other mount points.
* The extension intentionally preserves `plocate` first so fast matches appear immediately; hardware-find results are appended.

## Acknowledgement
Thanks to the original developer, [hassanradwannn](https://github.com/hassanradwannn).  
This fork extends the original work by adding support for searching hardware-mounted drives (e.g. `/run/media`).
