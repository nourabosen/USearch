# main.py

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, PreferencesEvent, PreferencesUpdateEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
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
        # Store current preferences
        self.preferences = {}

class PreferencesUpdateEventListener(EventListener):
    def on_event(self, event, extension):
        extension.preferences[event.id] = event.new_value
        if event.id == 'limit':
            locator.set_limit(event.new_value)
        elif event.id in ('hardware_prefix', 'raw_prefix'):
            locator.update_prefixes(
                hardware_prefix=extension.preferences.get('hardware_prefix', 'hw'),
                raw_prefix=extension.preferences.get('raw_prefix', 'r')
            )

class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        extension.preferences = event.preferences
        locator.set_limit(event.preferences['limit'])
        locator.update_prefixes(
            hardware_prefix=event.preferences.get('hardware_prefix', 'hw'),
            raw_prefix=event.preferences.get('raw_prefix', 'r')
        )

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        results = event.get_data()
        items = []
        for file in results:
            items.append(ExtensionSmallResultItem(
                icon='images/copy.png',
                name=file,
                on_enter=CopyToClipboardAction(file)
            ))
        return RenderResultListAction(items)

class KeywordQueryEventListener(EventListener):
    def __help(self, extension):
        hw_prefix = extension.preferences.get('hardware_prefix', 'hw')
        raw_prefix = extension.preferences.get('raw_prefix', 'r')
        keyword = extension.preferences.get('keyword', 's')

        items = []
        items.append(ExtensionSmallResultItem(
            icon='images/info.png',
            name=f'Normal search: {keyword} <pattern>',
            description='Fast indexed search + hardware drives',
            on_enter=SetUserQueryAction(f'{keyword} ')
        ))
        items.append(ExtensionSmallResultItem(
            icon='images/hardware.png',
            name=f'Hardware search: {keyword} {hw_prefix} <pattern>',
            description='Search only mounted drives (/media, /mnt, /run/media)',
            on_enter=SetUserQueryAction(f'{keyword} {hw_prefix} ')
        ))
        items.append(ExtensionSmallResultItem(
            icon='images/raw.png',
            name=f'Raw locate: {keyword} {raw_prefix} <args>',
            description='Raw plocate/locate arguments',
            on_enter=SetUserQueryAction(f'{keyword} {raw_prefix} ')
        ))
        return items

    def on_event(self, event, extension):
        arg = event.get_argument()
        items = []
        if arg is None or arg.strip() == '':
            items = self.__help(extension)
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
                        on_enter=SetUserQueryAction(f'{extension.preferences.get("keyword", "s")} ')
                    ))
                else:
                    alt_action = ExtensionCustomAction(results, True)
                    for file in results:
                        display_name = file if len(file) <= 80 else f"{file[:77]}..."
                        items.append(ExtensionSmallResultItem(
                            icon='images/ok.png',
                            name=display_name,
                            description=file,
                            on_enter=OpenAction(file),
                            on_alt_enter=alt_action
                        ))

                    # Determine mode for info line
                    hw_prefix = extension.preferences.get('hardware_prefix', 'hw').lower()
                    raw_prefix = extension.preferences.get('raw_prefix', 'r').lower()
                    arg_lower = arg.lower()

                    if arg_lower.startswith(f'{hw_prefix} '):
                        mode_info = "Hardware-only search"
                    elif arg_lower.startswith(f'{raw_prefix} '):
                        mode_info = "Raw locate search"
                    else:
                        mode_info = "Combined search (indexed + hardware)"

                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"Found {len(results)} results - {mode_info}",
                        description="Alt+Enter to copy all paths",
                        on_enter=SetUserQueryAction(f'{extension.preferences.get("keyword", "s")} ')
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
