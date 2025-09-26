from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.event import PreferencesEvent, PreferencesUpdateEvent, ItemEnterEvent
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
        locator.set_limit(event.preferences.get('limit', locator.limit))

class ItemEnterEventListener(EventListener):
    """
    Handles ExtensionCustomAction payloads and renders pages.
    Payload forms:
      - legacy: a list of file paths => copy to clipboard for each item
      - paging: {'type':'page','results':[...],'page':N,'per_page':M}
    """
    def on_event(self, event, extension):
        data = event.get_data()
        items = []

        # Legacy: list => show copy actions
        if isinstance(data, list):
            for f in data:
                items.append(ExtensionSmallResultItem(
                    icon='images/copy.png',
                    name=f,
                    on_enter=CopyToClipboardAction(f)
                ))
            return RenderResultListAction(items)

        # Paging
        if isinstance(data, dict) and data.get('type') == 'page':
            results = data.get('results', [])
            page = int(data.get('page', 0))
            per_page = int(data.get('per_page', locator.limit))
            start = page * per_page
            end = start + per_page
            slice_results = results[start:end]

            for file in slice_results:
                items.append(ExtensionSmallResultItem(
                    icon='images/ok.png',
                    name=file,
                    on_enter=OpenAction(file),
                    on_alt_enter=ExtensionCustomAction(results, True)
                ))

            if end < len(results):
                more_payload = {'type': 'page', 'results': results, 'page': page + 1, 'per_page': per_page}
                items.append(ExtensionSmallResultItem(
                    icon='images/info.png',
                    name=f"More results ({len(results) - end} remaining) — press Enter to load",
                    on_enter=ExtensionCustomAction(more_payload, True)
                ))
            else:
                items.append(ExtensionSmallResultItem(
                    icon='images/info.png',
                    name=f"End of results — {len(results)} total",
                    on_enter=SetUserQueryAction('')
                ))

            return RenderResultListAction(items)

        # Fallback error
        items.append(ExtensionSmallResultItem(
            icon='images/error.png',
            name='Unrecognized event data',
            on_enter=CopyToClipboardAction(str(data))
        ))
        return RenderResultListAction(items)

class KeywordQueryEventListener(EventListener):
    def __help(self):
        items = []
        items.append(ExtensionSmallResultItem(
            icon='images/info.png',
            name='Hint: s <pattern>  — fast indexed search (plocate)',
            on_enter=SetUserQueryAction('s ')
        ))
        items.append(ExtensionSmallResultItem(
            icon='images/info.png',
            name='Hint: s hw <pattern> — live search on mounted media (/run/media)',
            on_enter=SetUserQueryAction('s hw ')
        ))
        items.append(ExtensionSmallResultItem(
            icon='images/info.png',
            name='Hint: s r <locate-args> — raw plocate/locate args',
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
                results = locator.run(arg)

                # Show first page
                page = 0
                per_page = locator.limit
                start = page * per_page
                end = start + per_page
                page_slice = results[start:end]

                for file in page_slice:
                    items.append(ExtensionSmallResultItem(
                        icon='images/ok.png',
                        name=file,
                        on_enter=OpenAction(file),
                        on_alt_enter=ExtensionCustomAction(results, True)
                    ))

                if end < len(results):
                    payload = {'type': 'page', 'results': results, 'page': page + 1, 'per_page': per_page}
                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"More results ({len(results) - end} remaining) — press Enter to load",
                        on_enter=ExtensionCustomAction(payload, True)
                    ))
                else:
                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"Found {len(results)} result(s)",
                        on_enter=SetUserQueryAction('')
                    ))

            except Exception as e:
                error_info = str(e)
                items = [ExtensionSmallResultItem(
                    icon='images/error.png',
                    name=error_info,
                    on_enter=CopyToClipboardAction(error_info)
                )]

        return RenderResultListAction(items)

if __name__ == '__main__':
    SearchFileExtension().run()
