from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
from ulauncher.api.shared.event import PreferencesEvent
from ulauncher.api.shared.event import PreferencesUpdateEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
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
        results = event.get_data()
        items = []
        for file in results:
            items.append(ExtensionSmallResultItem(icon='images/copy.png',
                name=file,
                on_enter=CopyToClipboardAction(file)))
        return RenderResultListAction(items)

class KeywordQueryEventListener(EventListener):
    def __help(self):
        items = []
        items.append(ExtensionSmallResultItem(icon='images/info.png',
            name='File search: s <pattern>',
            description='Fast indexed search + hardware drives',
            on_enter=SetUserQueryAction('s ')
        ))
        items.append(ExtensionSmallResultItem(icon='images/folder.png',
            name='Folder search: s folder <pattern>',
            description='Search for directories only',
            on_enter=SetUserQueryAction('s folder ')
        ))
        items.append(ExtensionSmallResultItem(icon='images/hardware.png',
            name='Hardware files: s hw <pattern>',
            description='Search only mounted drives (/media, /mnt, /run/media)',
            on_enter=SetUserQueryAction('s hw ')
        ))
        items.append(ExtensionSmallResultItem(icon='images/hardware-folder.png',
            name='Hardware folders: s hw folder <pattern>',
            description='Search folders on mounted drives only',
            on_enter=SetUserQueryAction('s hw folder ')
        ))
        items.append(ExtensionSmallResultItem(icon='images/raw.png',
            name='Raw locate: s r <args>',
            description='Raw plocate/locate arguments',
            on_enter=SetUserQueryAction('s r ')
        ))
        return items
                
    def on_event(self, event, extension):
        arg = event.get_argument()
        items = []

        if arg is None or arg.strip() == '':
            items = self.__help()
        else:
            try:
                print(f"Ulauncher searching for: '{arg}'")
                results = locator.run(arg)
                print(f"Ulauncher got {len(results)} results")
                
                if not results:
                    # Determine search type for better error message
                    if arg.lower().startswith('folder'):
                        search_type = "folders"
                    elif arg.lower().startswith('hw folder'):
                        search_type = "folders on hardware drives"
                    elif arg.lower().startswith('hw'):
                        search_type = "files on hardware drives"
                    else:
                        search_type = "files"
                    
                    items.append(ExtensionSmallResultItem(
                        icon='images/warning.png',
                        name=f'No {search_type} found',
                        description=f'No results matching "{arg}"',
                        on_enter=SetUserQueryAction('s ')
                    ))
                else:
                    alt_action = ExtensionCustomAction(results, True)
                    
                    # Determine if we're searching folders to use appropriate icons/actions
                    is_folder_search = arg.lower().startswith('folder') or arg.lower().startswith('hw folder')
                    
                    for file in results:
                        # Truncate long filenames for display
                        display_name = file if len(file) <= 80 else f"{file[:77]}..."
                        
                        # Use folder icon for directories, file icon for files
                        icon = 'images/folder.png' if is_folder_search else 'images/file.png'
                        
                        # For folders, open in file manager; for files, open with default app
                        if is_folder_search:
                            enter_action = RunScriptAction(f'xdg-open "{file}"')
                        else:
                            enter_action = OpenAction(file)
                        
                        items.append(ExtensionSmallResultItem(
                            icon=icon,
                            name=display_name,
                            description=file,  # Full path in description
                            on_enter=enter_action,
                            on_alt_enter=alt_action
                        ))
                    
                    # Add info item showing search mode
                    if arg.lower().startswith('hw folder'):
                        mode_info = "Hardware folders search"
                    elif arg.lower().startswith('folder'):
                        mode_info = "Folder search"
                    elif arg.lower().startswith('hw '):
                        mode_info = "Hardware files search"
                    elif arg.lower().startswith('r '):
                        mode_info = "Raw locate search"
                    else:
                        mode_info = "Combined search (indexed + hardware)"
                    
                    result_type = "folders" if is_folder_search else "files"
                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"Found {len(results)} {result_type} - {mode_info}",
                        description="Alt+Enter to copy all paths",
                        on_enter=SetUserQueryAction('s ')
                    ))
                        
            except Exception as e:
                error_info = str(e)
                print(f"Ulauncher error: {error_info}")
                items = [ExtensionSmallResultItem(
                    icon='images/error.png',
                    name='Search error',
                    description=error_info,
                    on_enter=CopyToClipboardAction(error_info)
                )]
        
        return RenderResultListAction(items)

if __name__ == '__main__':
    SearchFileExtension().run()
