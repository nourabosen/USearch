# FileFlow — Ulauncher Extension

**Find files and folders quickly using the system locate database (plocate/locate) with mounted hardware drive support and intelligent "Open With" functionality.**

This extension combines the speed of `plocate` with live scanning for mounted media and dynamic application detection for flexible file opening options.

## Features
- **Fast indexed search** using `plocate` or `locate`
- **Folder search capability** to quickly locate directories
- **Automatic hardware drive scanning** of mounted media (`/run/media`, `/media`, `/mnt`) using `find`
- **Dynamic "Open With" menu** that detects applications installed on your system
- **Smart file type detection** suggesting relevant applications for different file types
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
- **Folder search**: `s dir pattern` or `s folder pattern`  
  Search for directories only
- **Hardware-only search**: `s hw pattern`  
  Live scan only on mounted media (USB drives, external HDDs, etc.)
- **Raw locate search**: `s r locate-args`  
  Direct arguments to locate/plocate (e.g., `s r -i *.pdf`)

### Examples:
```bash
s project.docx              # Combined search (indexed + hardware)
s dir documents            # Search for directories named "documents"
s hw vacation-photos        # Hardware drives only
s r -i \.pdf$              # Raw regex search for PDF files
s folder projects          # Alternative folder search syntax
```

### Navigation & Actions:
- **Enter**: Open file/folder with default application
- **Alt+Enter**: Show "Open With" menu with available applications
- **Ctrl+Enter**: Copy all file paths to clipboard
- **Clean display**: Shows filename with parent directory context
- **Full path**: Available in description tooltip

### Open With Feature:
The extension dynamically detects applications installed on your system and suggests relevant options based on file type:
- **Text files**: Available text editors (VS Code, gedit, Vim, etc.)
- **PDFs**: PDF viewers (Evince, Okular, browsers)
- **Images**: Image viewers and editors (GIMP, eog, etc.)
- **Media**: Media players (VLC, MPV, etc.)
- **Directories**: File managers and terminals

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

The extension intelligently combines multiple search methods and dynamic application detection:

### Search Methods:
1. **Indexed Search** (Fast): Uses `plocate/locate` with system database
2. **Hardware Search** (Comprehensive): Uses `find` on mounted drives
3. **Folder Search**: Specifically targets directories only

### Application Detection:
- **Dynamic scanning**: Detects applications installed in common directories
- **File type matching**: Suggests relevant apps based on file extensions
- **System integration**: Uses `xdg-open` and `gio open` as fallbacks

### Search Locations:
- `/run/media/*/*` - User-mounted drives (typical for USB sticks)
- `/media/*` - System-mounted media
- `/mnt/*` - Traditional mount points

## Configuration

Adjust settings in Ulauncher → Preferences → Extensions → FileFlow:

- **Keyword**: Change the activation keyword (default: `s`)
- **Limit**: Maximum number of results to display

## Troubleshooting

### Hardware drives not showing?
1. Check if drives are properly mounted:
   ```bash
   ls /run/media/*/* /media/* /mnt/*
   ```

2. Verify the extension can detect paths by checking Ulauncher console logs

### Open With menu missing applications?
- The extension dynamically detects installed applications
- Applications must be in your `PATH` or standard directories
- Check if applications are properly installed and executable

### Search is slow?
- Hardware searches on large drives may take a few seconds
- The extension uses timeouts to prevent hanging
- Normal searches (non-hardware) remain instant

### No results found?
- Ensure `plocate/locate` is installed and database is updated
- Check file permissions on the drives you're searching
- Try hardware-only mode: `s hw filename`
- Try folder search: `s dir foldername`

### Application not opening files?
- Ensure the application is properly installed
- Check file permissions and associations
- Try using the "Default Application" option in Open With menu

## Changelog

### Version 2.0
- **Added folder search** with `s dir` and `s folder` commands
- **Dynamic Open With menu** that detects installed applications
- **File type-specific application suggestions**
- **Improved path display** showing filename with parent context
- **Enhanced navigation** with Alt+Enter for Open With menu

### Version 1.0
- Initial release with basic file search
- Hardware drive scanning support
- Multiple search modes

## Acknowledgments
Based on the original work by [hassanradwannn](https://github.com/hassanradwannn).  
Extended with hardware-mounted drive support and dynamic application detection for complete file management capability.

Icons from [Flaticon](https://www.flaticon.com/)
