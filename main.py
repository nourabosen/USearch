from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.event import PreferencesEvent
from ulauncher.api.shared.event import PreferencesUpdateEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
import subprocess
import os
import shutil
import glob

from locator import Locator

locator = Locator()

class SearchFileExtension(Extension):
    def __init__(self):
        super(SearchFileExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesUpdateEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

class PreferencesUpdateEventListener(EventListener):
    def on_event(self, event, extension):
        if event.id == 'limit':
            locator.set_limit(event.new_value)

class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        locator.set_limit(event.preferences['limit'])

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        if isinstance(data, dict):
            if data.get('type') == 'open_with':
                # Handle open with action
                file_path = data['file_path']
                app_command = data['app_command']
                try:
                    subprocess.Popen([app_command, file_path])
                except Exception as e:
                    print(f"Error opening with {app_command}: {e}")
            elif data.get('type') == 'open_with_trigger':
                # Trigger Open With menu - set the query
                file_path = data['file_path']
                return RenderResultListAction([ExtensionResultItem(
                    icon='images/info.png',
                    name='Press Enter to continue to Open With menu',
                    description='This will switch to Open With mode',
                    on_enter=SetUserQueryAction(f's openwith {file_path}')
                )])
        else:
            # Handle copy all paths (original functionality)
            results = data if isinstance(data, list) else []
            items = []
            for file in results:
                items.append(ExtensionSmallResultItem(icon='images/copy.png',
                    name=file,
                    on_enter=CopyToClipboardAction(file)))
            return RenderResultListAction(items)

class KeywordQueryEventListener(EventListener):
    def __init__(self):
        self.common_apps_cache = None
        self.cache_timestamp = 0
        self.cache_timeout = 300  # 5 minutes cache
    
    def __help(self):
        # Debug image paths
        extension_path = os.path.dirname(os.path.abspath(__file__))
        images_dir = os.path.join(extension_path, 'images')
        print(f"Extension path: {extension_path}")
        print(f"Images dir: {images_dir}")
        
        if os.path.exists(images_dir):
            print("Images directory exists")
            for img in os.listdir(images_dir):
                print(f"Found image: {img}")
        else:
            print("Images directory does not exist!")
        
        items = []
        items.append(ExtensionResultItem(icon='images/info.png',
            name='File search: s <pattern>',
            description='Fast indexed search + hardware drives',
            on_enter=SetUserQueryAction('s ')
        ))
        items.append(ExtensionResultItem(icon='images/folder.png',
            name='Folder search: s dir <pattern>',
            description='Search for directories only',
            on_enter=SetUserQueryAction('s dir ')
        ))
        items.append(ExtensionResultItem(icon='images/hardware.png',
            name='Hardware search: s hw <pattern>',
            description='Search only mounted drives (/media, /mnt, /run/media)',
            on_enter=SetUserQueryAction('s hw ')
        ))
        items.append(ExtensionResultItem(icon='images/raw.png',
            name='Raw locate: s r <args>',
            description='Raw plocate/locate arguments',
            on_enter=SetUserQueryAction('s r ')
        ))
        return items
    
    def __format_display_name(self, file_path):
        """Format the display name to show filename/extension with parent context"""
        try:
            # Get the filename and extension
            filename = os.path.basename(file_path)
            dir_path = os.path.dirname(file_path)
            
            # Extract useful path components for context
            path_parts = file_path.split('/')
            
            # Look for hardware mount points and user directories
            hardware_bases = ["/run/media", "/media", "/mnt"]
            user_name = None
            volume_name = None
            parent_dir = None
            
            for i, part in enumerate(path_parts):
                if part in hardware_bases and i + 2 < len(path_parts):
                    # Found a hardware base path like /run/media
                    user_name = path_parts[i + 1] if i + 1 < len(path_parts) else None
                    volume_name = path_parts[i + 2] if i + 2 < len(path_parts) else None
                    # Get the parent directory of the file (the folder containing the file)
                    if len(path_parts) > i + 3:
                        parent_dir = path_parts[-2]  # Second last part is the parent directory
                    break
            
            # Build the display name
            if user_name and volume_name:
                if parent_dir:
                    return f"{user_name}/{volume_name}/.../[{parent_dir}]/{filename}"
                else:
                    return f"{user_name}/{volume_name}/.../{filename}"
            elif volume_name:
                if parent_dir:
                    return f"{volume_name}/.../[{parent_dir}]/{filename}"
                else:
                    return f"{volume_name}/.../{filename}"
            else:
                # Fallback: just show the filename with parent directory context
                parent_dir = os.path.basename(dir_path)
                if parent_dir:
                    return f".../[{parent_dir}]/{filename}"
                else:
                    return filename
                    
        except Exception as e:
            print(f"Error formatting display name for {file_path}: {e}")
            return os.path.basename(file_path)
    
    def __get_common_applications(self):
        """Dynamically discover common applications on the system"""
        import time
        
        # Use cached results if recent enough
        current_time = time.time()
        if (self.common_apps_cache and 
            current_time - self.cache_timestamp < self.cache_timeout):
            return self.common_apps_cache
        
        print("Scanning for available applications...")
        common_apps = []
        
        # Common application directories to search
        app_dirs = [
            '/usr/bin',
            '/usr/local/bin',
            '/bin',
            '/snap/bin',
            os.path.expanduser('~/.local/bin'),
        ]
        
        # Common desktop applications (without .desktop extension)
        common_desktop_apps = [
            # File managers
            'nautilus', 'dolphin', 'thunar', 'pcmanfm', 'nemo', 'caja',
            # Text editors
            'gedit', 'code', 'subl', 'vim', 'nano', 'mousepad', 'kate', 'geany',
            # Image viewers
            'eog', 'feh', 'gimp', 'gthumb', 'shotwell',
            # PDF viewers
            'evince', 'okular', 'atril',
            # Media players
            'vlc', 'mpv', 'celluloid', 'rhythmbox', 'audacious', 'smplayer',
            # Browsers
            'firefox', 'google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser',
            # Terminals
            'gnome-terminal', 'konsole', 'xfce4-terminal', 'terminator', 'tilix',
            # Development
            'code', 'subl', 'vim', 'nvim', 'emacs',
            # Office
            'libreoffice', 'soffice',
        ]
        
        # Check which apps exist in PATH
        for app in common_desktop_apps:
            if shutil.which(app):
                common_apps.append(app)
        
        # Search application directories for additional binaries
        for app_dir in app_dirs:
            if os.path.isdir(app_dir):
                try:
                    for app in os.listdir(app_dir):
                        app_path = os.path.join(app_dir, app)
                        if (os.path.isfile(app_path) and os.access(app_path, os.X_OK) and
                            not app.startswith('.') and len(app) > 2):
                            common_apps.append(app)
                except (OSError, PermissionError):
                    continue
        
        # Remove duplicates and sort
        common_apps = sorted(list(set(common_apps)))
        print(f"Found {len(common_apps)} applications: {common_apps}")
        
        # Cache the results
        self.common_apps_cache = common_apps
        self.cache_timestamp = current_time
        
        return common_apps
    
    def __get_file_type_specific_apps(self, file_path):
        """Get appropriate applications based on file type"""
        common_apps = self.__get_common_applications()
        file_type_apps = []
        
        # Default applications that should always be available
        default_apps = ['xdg-open', 'gio']
        
        # Check if it's a directory
        if os.path.isdir(file_path):
            folder_apps = ['nautilus', 'dolphin', 'thunar', 'pcmanfm', 'nemo', 'caja', 
                          'gnome-terminal', 'konsole', 'xfce4-terminal', 'terminator']
            for app in folder_apps:
                if app in common_apps:
                    file_type_apps.append(app)
        
        else:
            # Get file extension
            _, ext = os.path.splitext(file_path.lower())
            ext = ext.lstrip('.')
            
            # Text files
            if ext in ['txt', 'md', 'log', 'conf', 'ini', 'py', 'js', 'html', 'css', 'json', 'xml', 'sh', 'bash']:
                text_apps = ['gedit', 'code', 'subl', 'vim', 'nano', 'mousepad', 'kate', 'geany']
                for app in text_apps:
                    if app in common_apps:
                        file_type_apps.append(app)
            
            # PDF files
            elif ext == 'pdf':
                pdf_apps = ['evince', 'okular', 'atril', 'firefox', 'chromium']
                for app in pdf_apps:
                    if app in common_apps:
                        file_type_apps.append(app)
            
            # Image files
            elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'tiff']:
                image_apps = ['eog', 'feh', 'gimp', 'gthumb', 'shotwell', 'firefox']
                for app in image_apps:
                    if app in common_apps:
                        file_type_apps.append(app)
            
            # Video files
            elif ext in ['mp4', 'avi', 'mkv', 'mov', 'webm', 'flv', 'wmv', 'm4v']:
                video_apps = ['vlc', 'mpv', 'celluloid', 'smplayer', 'firefox']
                for app in video_apps:
                    if app in common_apps:
                        file_type_apps.append(app)
            
            # Audio files
            elif ext in ['mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac', 'wma']:
                audio_apps = ['vlc', 'rhythmbox', 'audacious', 'smplayer']
                for app in audio_apps:
                    if app in common_apps:
                        file_type_apps.append(app)
            
            # Archive files
            elif ext in ['zip', 'tar', 'gz', 'bz2', 'xz', 'rar', '7z']:
                archive_apps = ['file-roller', 'ark', 'xarchiver']
                for app in archive_apps:
                    if app in common_apps:
                        file_type_apps.append(app)
        
        # Add default applications
        for app in default_apps:
            if app in common_apps:
                file_type_apps.append(app)
        
        # Remove duplicates and return
        return list(set(file_type_apps))
    
    def __get_friendly_app_name(self, app_command):
        """Convert command name to friendly display name"""
        friendly_names = {
            'xdg-open': 'Default Application',
            'gio': 'System Default',
            'nautilus': 'File Manager (Nautilus)',
            'dolphin': 'File Manager (Dolphin)',
            'thunar': 'File Manager (Thunar)',
            'pcmanfm': 'File Manager (PCManFM)',
            'nemo': 'File Manager (Nemo)',
            'caja': 'File Manager (Caja)',
            'gedit': 'Text Editor (Gedit)',
            'code': 'VS Code',
            'subl': 'Sublime Text',
            'vim': 'Vim',
            'nano': 'Nano',
            'mousepad': 'Text Editor (Mousepad)',
            'kate': 'Text Editor (Kate)',
            'geany': 'Text Editor (Geany)',
            'eog': 'Image Viewer (Eye of GNOME)',
            'feh': 'Image Viewer (Feh)',
            'gimp': 'GIMP',
            'gthumb': 'Image Viewer (gThumb)',
            'shotwell': 'Image Viewer (Shotwell)',
            'evince': 'Document Viewer (Evince)',
            'okular': 'Document Viewer (Okular)',
            'atril': 'Document Viewer (Atril)',
            'vlc': 'VLC Media Player',
            'mpv': 'MPV Player',
            'celluloid': 'Video Player (Celluloid)',
            'rhythmbox': 'Music Player (Rhythmbox)',
            'audacious': 'Music Player (Audacious)',
            'smplayer': 'Media Player (SMPlayer)',
            'firefox': 'Firefox',
            'google-chrome': 'Google Chrome',
            'google-chrome-stable': 'Google Chrome',
            'chromium': 'Chromium',
            'chromium-browser': 'Chromium',
            'gnome-terminal': 'Terminal (GNOME)',
            'konsole': 'Terminal (Konsole)',
            'xfce4-terminal': 'Terminal (XFCE)',
            'terminator': 'Terminal (Terminator)',
            'tilix': 'Terminal (Tilix)',
            'libreoffice': 'LibreOffice',
            'soffice': 'LibreOffice',
            'file-roller': 'Archive Manager',
            'ark': 'Archive Manager (Ark)',
            'xarchiver': 'Archive Manager (Xarchiver)',
        }
        
        return friendly_names.get(app_command, app_command)
    
    def __get_open_with_apps(self, file_path):
        """Get applications for opening files based on what's available on the system"""
        apps = []
        
        # Get file type specific applications
        file_type_apps = self.__get_file_type_specific_apps(file_path)
        
        for app_command in file_type_apps:
            app_name = self.__get_friendly_app_name(app_command)
            apps.append((app_name, app_command))
        
        # Add a custom command option
        apps.append(('Custom Command...', 'custom'))
        
        return apps

    def __create_open_with_menu(self, file_path):
        """Create the Open With menu"""
        items = []
        
        # Add a header item
        items.append(ExtensionResultItem(
            icon='images/app.png',
            name=f"Open '{os.path.basename(file_path)}' with...",
            description='Choose an application to open this file',
            on_enter=HideWindowAction()
        ))
        
        # Get available applications
        apps = self.__get_open_with_apps(file_path)
        
        for app_name, app_command in apps:
            if app_command == 'custom':
                # Custom command option
                items.append(ExtensionResultItem(
                    icon='images/terminal.png',
                    name=app_name,
                    description='Enter a custom command to open this file',
                    on_enter=DoNothingAction()
                ))
            else:
                # Check if the application exists
                app_exists = shutil.which(app_command) is not None
                
                items.append(ExtensionResultItem(
                    icon='images/ok.png' if app_exists else 'images/warning.png',
                    name=app_name,
                    description=f"Press Enter to open with {app_command}" if app_exists else f"Application not found: {app_command}",
                    on_enter=ExtensionCustomAction({
                        'type': 'open_with',
                        'file_path': file_path,
                        'app_command': app_command
                    }, True) if app_exists else DoNothingAction()
                ))
        
        # Add back to search item
        items.append(ExtensionResultItem(
            icon='images/back.png',
            name='Back to search results',
            description='Return to the main search view',
            on_enter=SetUserQueryAction('s ')
        ))
        
        return items

    def on_event(self, event, extension):
        arg = event.get_argument()
        items = []

        # Check if this is an Open With menu request
        if arg and arg.startswith('openwith '):
            try:
                file_path = arg.split('openwith ', 1)[1].strip()
                if os.path.exists(file_path):
                    return RenderResultListAction(self.__create_open_with_menu(file_path))
                else:
                    items.append(ExtensionResultItem(
                        icon='images/error.png',
                        name='File not found',
                        description='The file does not exist anymore',
                        on_enter=SetUserQueryAction('s ')
                    ))
            except Exception as e:
                print(f"Error in openwith menu: {e}")
                items.append(ExtensionResultItem(
                    icon='images/error.png',
                    name='Error opening Open With menu',
                    description=str(e),
                    on_enter=SetUserQueryAction('s ')
                ))

        elif arg is None or arg.strip() == '':
            items = self.__help()
        else:
            try:
                print(f"Ulauncher searching for: '{arg}'")
                results = locator.run(arg)
                print(f"Ulauncher got {len(results)} results")
                
                if not results:
                    items.append(ExtensionResultItem(
                        icon='images/warning.png',
                        name='No results found',
                        description=f'No files matching "{arg}"',
                        on_enter=SetUserQueryAction('s ')
                    ))
                else:
                    alt_action = ExtensionCustomAction(results, True)
                    
                    for i, file_path in enumerate(results):
                        # Format the display name to show filename/extension with context
                        display_name = self.__format_display_name(file_path)
                        
                        # Check if it's a directory or file for icon
                        icon = 'images/folder.png' if os.path.isdir(file_path) else 'images/ok.png'
                        
                        # Create Open With trigger action
                        open_with_action = ExtensionCustomAction({
                            'type': 'open_with_trigger', 
                            'file_path': file_path
                        }, True)
                        
                        # Create the main search result item
                        items.append(ExtensionResultItem(
                            icon=icon,
                            name=display_name,
                            description=f"{file_path} | Alt+Enter for Open With",
                            on_enter=OpenAction(file_path),
                            on_alt_enter=open_with_action
                        ))
                    
                    # Add info item showing search mode
                    mode_info = "File search"
                    if arg.lower().startswith('hw '):
                        mode_info = "Hardware-only search"
                    elif arg.lower().startswith('r '):
                        mode_info = "Raw locate search"
                    elif arg.lower().startswith('dir ') or arg.lower().startswith('folder '):
                        mode_info = "Directory search"
                    
                    items.append(ExtensionResultItem(
                        icon='images/info.png',
                        name=f"Found {len(results)} results - {mode_info}",
                        description="Enter: Open | Alt+Enter: Open With | Ctrl+Enter: Copy all",
                        on_enter=SetUserQueryAction('s ')
                    ))
                        
            except Exception as e:
                error_info = str(e)
                print(f"Ulauncher error: {error_info}")
                items = [ExtensionResultItem(
                    icon='images/error.png',
                    name='Search error',
                    description=error_info,
                    on_enter=CopyToClipboardAction(error_info)
                )]
        
        return RenderResultListAction(items)

if __name__ == '__main__':
    SearchFileExtension().run()
