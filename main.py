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
            elif data.get('type') == 'open_with_menu':
                # This is the menu trigger, nothing to do here
                pass
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
    def __help(self):
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
    
    def __get_open_with_apps(self, file_path):
        """Get common applications for opening files based on file type"""
        apps = []
        
        # Check if it's a directory
        if os.path.isdir(file_path):
            apps.extend([
                ('File Manager (nautilus)', 'nautilus'),
                ('Terminal (gnome-terminal)', 'gnome-terminal'),
                ('VS Code', 'code'),
                ('File Manager (dolphin)', 'dolphin'),
                ('File Manager (thunar)', 'thunar'),
                ('File Manager (pcmanfm)', 'pcmanfm')
            ])
        else:
            # Get file extension
            _, ext = os.path.splitext(file_path.lower())
            
            if ext in ['.txt', '.md', '.log', '.conf', '.ini', '.py', '.js', '.html', '.css', '.json', '.xml']:
                apps.extend([
                    ('Text Editor (gedit)', 'gedit'),
                    ('VS Code', 'code'),
                    ('Sublime Text', 'subl'),
                    ('Vim', 'vim'),
                    ('Nano', 'nano'),
                    ('Mousepad', 'mousepad')
                ])
            elif ext in ['.pdf']:
                apps.extend([
                    ('Document Viewer (evince)', 'evince'),
                    ('Okular', 'okular'),
                    ('Firefox', 'firefox'),
                    ('Chrome', 'google-chrome-stable')
                ])
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
                apps.extend([
                    ('Image Viewer (eog)', 'eog'),
                    ('GIMP', 'gimp'),
                    ('Feh', 'feh'),
                    ('Firefox', 'firefox')
                ])
            elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv']:
                apps.extend([
                    ('VLC', 'vlc'),
                    ('MPV', 'mpv'),
                    ('Celluloid', 'celluloid'),
                    ('Firefox', 'firefox')
                ])
            elif ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac']:
                apps.extend([
                    ('Music Player (rhythmbox)', 'rhythmbox'),
                    ('VLC', 'vlc'),
                    ('Audacious', 'audacious')
                ])
            else:
                # Generic applications for unknown file types
                apps.extend([
                    ('Text Editor (gedit)', 'gedit'),
                    ('VS Code', 'code'),
                    ('File Manager (nautilus)', 'nautilus')
                ])
        
        # Add generic applications
        apps.extend([
            ('Default Application (xdg-open)', 'xdg-open'),
            ('System Default', 'gio open')
        ])
        
        # Remove duplicates and return
        seen = set()
        return [app for app in apps if not (app in seen or seen.add(app))]

    def __create_open_with_menu(self, file_path, query):
        """Create the Open With menu when left arrow is pressed"""
        items = []
        
        # Add a header item
        items.append(ExtensionResultItem(
            icon='images/app.png',
            name=f"Open '{os.path.basename(file_path)}' with...",
            description='Choose an application to open this file',
            on_enter=HideWindowAction(),
            on_alt_enter=HideWindowAction()
        ))
        
        # Get available applications
        apps = self.__get_open_with_apps(file_path)
        
        for app_name, app_command in apps:
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
                }, True) if app_exists else DoNothingAction(),
                on_alt_enter=ExtensionCustomAction({
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
            on_enter=SetUserQueryAction('s ' + query.split(' ', 1)[1] if ' ' in query else 's '),
            on_alt_enter=SetUserQueryAction('s ' + query.split(' ', 1)[1] if ' ' in query else 's ')
        ))
        
        return items

    def on_event(self, event, extension):
        arg = event.get_argument()
        query = event.get_query() or ""
        items = []

        # Check if this is an Open With menu request (query starts with "s openwith ")
        if query.startswith("s openwith ") and len(query.split()) >= 3:
            try:
                file_path = ' '.join(query.split()[2:])
                if os.path.exists(file_path):
                    return RenderResultListAction(self.__create_open_with_menu(file_path, query))
            except:
                pass

        if arg is None or arg.strip() == '':
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
                        
                        # Create the main search result item
                        item = ExtensionResultItem(
                            icon=icon,
                            name=display_name,
                            description=file_path,  # Full path in description
                            on_enter=OpenAction(file_path),
                            on_alt_enter=alt_action
                        )
                        
                        # Add Open With action on left arrow (secondary action)
                        open_with_action = SetUserQueryAction(f's openwith {file_path}')
                        item.on_keyboard_enter = open_with_action
                        
                        items.append(item)
                    
                    # Add info item showing search mode
                    mode_info = "File search"
                    if arg.lower().startswith('hw '):
                        mode_info = "Hardware-only search"
                    elif arg.lower().startswith('r '):
                        mode_info = "Raw locate search"
                    elif arg.lower().startswith('dir ') or arg.lower().startswith('folder '):
                        mode_info = "Directory search"
                    
                    info_item = ExtensionResultItem(
                        icon='images/info.png',
                        name=f"Found {len(results)} results - {mode_info}",
                        description="Enter: Open | Alt+Enter: Copy all | ←: Open With",
                        on_enter=SetUserQueryAction('s ')
                    )
                    items.append(info_item)
                        
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

# Add missing import
import shutil

if __name__ == '__main__':
    SearchFileExtension().run()
