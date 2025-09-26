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
                    items.append(ExtensionSmallResultItem(
                        icon='images/warning.png',
                        name='No results found',
                        description=f'No files or folders matching "{arg}"',
                        on_enter=SetUserQueryAction('s ')
                    ))
                else:
                    alt_action = ExtensionCustomAction(results, True)
                    
                    for file_path in results:
                        # Truncate long paths for display
                        display_name = file_path if len(file_path) <= 80 else f"{file_path[:77]}..."
                        
                        # Check if it's a directory to determine icon and action
                        is_directory = os.path.isdir(file_path) if os.path.exists(file_path) else file_path.endswith('/')
                        
                        icon = 'images/folder.png' if is_directory else 'images/file.png'
                        
                        if is_directory:
                            enter_action = RunScriptAction(f'xdg-open "{file_path}"')
                        else:
                            enter_action = OpenAction(file_path)
                        
                        items.append(ExtensionSmallResultItem(
                            icon=icon,
                            name=display_name,
                            description=file_path,
                            on_enter=enter_action,
                            on_alt_enter=alt_action
                        ))
                    
                    # Add info item
                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"Found {len(results)} results",
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
