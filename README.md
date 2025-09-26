# USearch — Ulauncher Extension

**Quickly find files and folders using the system `plocate/locate` database, with live scans of mounted drives.**

USearch combines the speed of `plocate` with a fallback live search, making files and folders on external drives discoverable even if they’re excluded from the locate database.

---

## ✨ Features

* **Fast indexed search** with `plocate` or `locate`
* **Folder-only search mode** for directories
* **Live scanning of mounted hardware** (`/run/media`, `/media`, `/mnt`) using `find`
* **Merged results** with duplicates removed (indexed results always appear first)
* **Paginated results** in Ulauncher (`More results` item loads the next page)
* **Flexible search modes**:

  * `s <pattern>` — normal file search
  * `s folder <pattern>` — directories only
  * `s hw <pattern>` — mounted hardware only
  * `s hw folder <pattern>` — hardware directories only
  * `s r <locate-args>` — raw locate mode (advanced)
* **Smart actions**:

  * Files open with default apps
  * Folders open in the file manager
* **Alt+Enter** on a result copies the full result list
* **Configurable results-per-page** via Ulauncher preferences (`limit`)
* **Smart icons** (different for files and folders)
* **Context-aware error messages**

---

## 🚀 Usage

### Trigger

* Default keyword: `s`
* Example: `s project`

### Examples

* `s davinci.png` → indexed file search
* `s folder projects` → directories only
* `s hw photo.jpg` → live scan on mounted drives
* `s hw folder documents` → hardware directories only
* `s r -S .png` → pass raw arguments to `locate/plocate`

### Navigation

* **Enter**: Open file/folder
* **Arrow keys**: Navigate results
* **More results (...)**: Appears at the end of each page → press Enter to load more
* **Alt+Enter**: Copy all results

---

## ⚙️ Installation

1. **Install `plocate` or `locate`**

   * Debian/Ubuntu:

     ```bash
     sudo apt install plocate
     ```
   * Fedora:

     ```bash
     sudo dnf install plocate
     ```
   * Alternative (slower):

     ```bash
     sudo apt install mlocate
     ```

2. **Initialize/refresh the database**

   ```bash
   sudo updatedb
   ```

   For `plocate`, enable automatic updates:

   ```bash
   sudo systemctl enable --now plocate-updatedb.timer
   ```

3. **Install the extension**

   * Clone or copy this repo into your Ulauncher extensions folder
   * Or install via the Ulauncher extension manager (if published)

---

## 📝 Notes

* Searches run in two stages:

  1. **Indexed search** (`plocate/locate`) → fast
  2. **Live search** (`find` on hardware paths) → slower, especially for large drives
* To include external drives in system indexing, edit `/etc/updatedb.conf` and remove `/run` and `/media` from `PRUNEPATHS`, then run:

  ```bash
  sudo updatedb
  ```
* Live search paths: `/run/media`, `/media`, `/mnt`

  * You can add more in `locator.hardware_paths` inside `locator.py`
* Indexed results are always prioritized before live scan results

---

## 🙏 Acknowledgements

* Original developer: [hassanradwannn](https://github.com/hassanradwannn)
* Icon: [Flaticon](https://www.flaticon.com/free-icon/search-file_11677437)

This fork adds:
* Folder search modes
* Hardware-mounted drive support
