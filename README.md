# USearch — Ulauncher Extension

**Find files quickly using the system locate database (plocate/locate) and include mounted hardware drives by performing a live scan.**

This extension combines the speed of `plocate` with a fallback live-search for mounted media, allowing external drives under `/run/media`, `/media`, or `/mnt` to be discoverable even if the locate database excludes them.

## Features
- **Fast indexed search** using `plocate` or `locate`
- **Automatic hardware drive scanning** of mounted media (`/run/media`, `/media`, `/mnt`) using `find`
- **Three search modes:**
  - Normal: Combined indexed + hardware search
  - Hardware-only: Live scan only on mounted drives
  - Raw: Direct locate arguments for advanced users
- **Merges and de-duplicates results** (locate results appear first)
- **Configurable results limit** via Ulauncher preferences
- **Fast and responsive** with optimized hardware scanning

## Usage
Trigger with your configured keyword (default: `s`) followed by your query.

### Search Modes:
- **Normal search**: `s pattern`  
  Fast indexed search combined with hardware drive scan
- **Hardware-only search**: `s hw pattern`  
  Live scan only on mounted media (USB drives, external HDDs, etc.)
- **Raw locate search**: `s r locate-args`  
  Direct arguments to locate/plocate (e.g., `s r -i *.png`)

### Examples:
```bash
s project.docx              # Combined search (indexed + hardware)
s hw vacation-photos        # Hardware drives only
s r -i \.pdf$              # Raw regex search for PDF files
```

### Navigation:
- **Enter**: Open file with default application
- **Alt+Enter**: Copy file path to clipboard
- Results show full path in description for easy identification

## Installation

### 1. Install Dependencies
Ensure `plocate` or `locate` is installed:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install plocate  # or mlocate
```

**Fedora/RHEL:**
```bash
sudo dnf install plocate
```

**Arch Linux:**
```bash
sudo pacman -S plocate
```

### 2. Set up Locate Database
Update the locate database to include your files:

```bash
sudo updatedb
```

For automatic updates (plocate systems):
```bash
sudo systemctl enable --now plocate-updatedb.timer
```

### 3. Install Extension
- Open Ulauncher preferences → Extensions
- Click "Add extension" and paste the extension URL
- Or manually copy to `~/.local/share/ulauncher/extensions/`

## How It Works

The extension intelligently combines two search methods:

1. **Indexed Search** (Fast): Uses `plocate/locate` with system database
2. **Hardware Search** (Comprehensive): Uses `find` on mounted drives

### Search Locations:
- `/run/media/*/*` - User-mounted drives (typical for USB sticks)
- `/media/*` - System-mounted media
- `/mnt/*` - Traditional mount points

## Configuration

Adjust settings in Ulauncher → Preferences → Extensions → USearch:

- **Keyword**: Change the activation keyword (default: `s`)
- **Limit**: Maximum number of results to display

## Troubleshooting

### Hardware drives not showing?
1. Check if drives are properly mounted:
   ```bash
   ls /run/media/*/* /media/* /mnt/*
   ```

2. Verify the extension can detect paths by checking Ulauncher console logs

### Search is slow?
- Hardware searches on large drives may take a few seconds
- The extension uses timeouts to prevent hanging
- Normal searches (non-hardware) remain instant

### No results found?
- Ensure `plocate/locate` is installed and database is updated
- Check file permissions on the drives you're searching
- Try hardware-only mode: `s hw filename`


## Acknowledgments
Based on the original work by [hassanradwannn]https://github.com/hassanradwannn).  
Extended with hardware-mounted drive support for complete file search capability.

Icon from [Flaticon](https://www.flaticon.com/free-icon/search-file_11677437)
