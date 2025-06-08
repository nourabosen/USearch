plocate finder
Extension for ulauncher to quickly find files on your system using the plocate command, which provides fast file indexing and searching capabilities.
Features

Fast File Search: Utilizes plocate to search files efficiently by leveraging an indexed database.
Two Search Modes:
Normal Mode: Search by exact file names (e.g., s davinci.png).
Raw Mode: Use regex patterns for advanced searches (e.g., s r .png to find all PNG files).


Result Limit: Configurable maximum number of results (default: 8).
Actions: Press Alt+Number to open files with xdg-open or Alt+Enter to copy file paths to clipboard.

Usage

Trigger the extension with the keyword s followed by your search term.
For raw mode, prepend r (e.g., s r .png to match files ending in .png).
Configure preferences in Ulauncher to adjust the result limit or locate options.

Installation

Ensure plocate is installed (sudo apt install plocate on Debian-based systems) and the database is updated (sudo updatedb).
Install the extension via Ulauncher's extension manager.

Support
For issues or suggestions, feel free to reach out to the developer, hassanradwannn.
