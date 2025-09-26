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

# Global locator instance with default prefixes
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
        elif event.id == 'hardware_prefix':
            # Get current raw prefix to update both together
            raw_prefix = extension.preferences.get('raw_prefix', 'r')
            locator.set_prefixes(event.new_value, raw_prefix)
        elif event.id == 'raw_prefix':
            # Get current hardware prefix to update both together
            hardware_prefix = extension.preferences.get('hardware_prefix', 'hw')
            locator.set_prefixes(hardware_prefix, event.new_value)

class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        # Set initial preferences
        locator.set_limit(event.preferences.get('limit', '10'))
        
        # Set initial prefixes
        hardware_prefix = event.preferences.get('hardware_prefix', 'hw')
        raw_prefix = event.preferences.get('raw_prefix', 'r')
        locator.set_prefixes(hardware_prefix, raw_prefix)
        
        print(f"Preferences loaded: limit={event.preferences.get('limit', '10')}, "
              f"hardware_prefix='{hardware_prefix}', raw_prefix='{raw_prefix}'")

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
    def __help(self, hardware_prefix='hw', raw_prefix='r'):
        items = []
        items.append(ExtensionSmallResultItem(icon='images/info.png',
            name=f'Normal search: s <pattern>',
            description='Fast indexed search + hardware drives',
            on_enter=SetUserQueryAction('s ')
        ))
        items.append(ExtensionSmallResultItem(icon='images/hardware.png',
            name=f'Hardware search: s {hardware_prefix} <pattern>',
            description='Search only mounted drives (/media, /mnt, /run/media)',
            on_enter=SetUserQueryAction(f's {hardware_prefix} ')
        ))
        items.append(ExtensionSmallResultItem(icon='images/raw.png',
            name=f'Raw locate: s {raw_prefix} <args>',
            description='Raw plocate/locate arguments',
            on_enter=SetUserQueryAction(f's {raw_prefix} ')
        ))
        items.append(ExtensionSmallResultItem(icon='images/settings.png',
            name='Customize search prefixes in preferences',
            description=f'Current: {hardware_prefix}=hardware, {raw_prefix}=raw',
            on_enter=SetUserQueryAction('ulauncher-preferences')
        ))
        return items
                
    def on_event(self, event, extension):
        arg = event.get_argument()
        items = []

        if arg is None or arg.strip() == '':
            # Get current prefixes for help display
            hardware_prefix = extension.preferences.get('hardware_prefix', 'hw')
            raw_prefix = extension.preferences.get('raw_prefix', 'r')
            items = self.__help(hardware_prefix, raw_prefix)
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
                    hardware_prefix = extension.preferences.get('hardware_prefix', 'hw')
                    raw_prefix = extension.preferences.get('raw_prefix', 'r')
                    
                    if arg.lower().startswith(f'{hardware_prefix.lower()} '):
                        mode_info = f"Hardware-only search (prefix: {hardware_prefix})"
                    elif arg.lower().startswith(f'{raw_prefix.lower()} '):
                        mode_info = f"Raw locate search (prefix: {raw_prefix})"
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
