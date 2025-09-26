from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
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
            name='Normal search: s <pattern>',
            description='Fast indexed search + hardware drives',
            on_enter=SetUserQueryAction('s ')
        ))
        items.append(ExtensionSmallResultItem(icon='images/hardware.png',
            name='Hardware search: s hw <pattern>',
            description='Search only mounted drives (/media, /mnt, /run/media)',
            on_enter=SetUserQueryAction('s hw ')
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
                        description=f'No files matching "{arg}"',
                        on_enter=SetUserQueryAction('s ')
                    ))
                else:
                    alt_action = ExtensionCustomAction(results, True)
                    for file in results:
                        # Truncate long filenames for display
                        display_name = file if len(file) <= 80 else f"{file[:77]}..."
                        items.append(ExtensionSmallResultItem(
                            icon='images/ok.png',
                            name=display_name,
                            description=file,  # Full path in description
                            on_enter=OpenAction(file),
                            on_alt_enter=alt_action
                        ))
                    
                    # Add info item showing search mode
                    if arg.lower().startswith('hw '):
                        mode_info = "Hardware-only search"
                    elif arg.lower().startswith('r '):
                        mode_info = "Raw locate search"
                    else:
                        mode_info = "Combined search (indexed + hardware)"
                    
                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"Found {len(results)} results - {mode_info}",
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
