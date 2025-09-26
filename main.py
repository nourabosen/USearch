from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import (
    KeywordQueryEvent,
    PreferencesEvent,
    PreferencesUpdateEvent,
    ItemEnterEvent
)
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action import (
    RenderResultListAction,
    OpenAction,
    CopyToClipboardAction,
    SetUserQueryAction,
    ExtensionCustomAction
)

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
    def on_event(self, event, extension):
        data = event.get_data()
        items = []

        # Legacy: list of paths (from older versions or alt-enter)
        if isinstance(data, list):
            for f in data:
                items.append(ExtensionSmallResultItem(
                    icon='images/copy.png',
                    name=f,
                    on_enter=CopyToClipboardAction(f)
                ))
            return RenderResultListAction(items)

        # Paging payload
        if isinstance(data, dict) and data.get('type') == 'page':
            results = data.get('results', [])
            page = int(data.get('page', 0))
            per_page = int(data.get('per_page', locator.limit or 10))
            start = page * per_page
            end = start + per_page
            slice_results = results[start:end]

            for file in slice_results:
                items.append(ExtensionSmallResultItem(
                    icon='images/ok.png',
                    name=file,
                    on_enter=OpenAction(file),
                    on_alt_enter=ExtensionCustomAction(results, keep_app_open=True)
                ))

            if end < len(results):
                more_payload = {
                    'type': 'page',
                    'results': results,
                    'page': page + 1,
                    'per_page': per_page
                }
                items.append(ExtensionSmallResultItem(
                    icon='images/info.png',
                    name=f"More results ({len(results) - end} remaining) — press Enter to load",
                    on_enter=ExtensionCustomAction(more_payload, keep_app_open=True)
                ))
            else:
                items.append(ExtensionSmallResultItem(
                    icon='images/info.png',
                    name=f"End of results — {len(results)} total",
                    on_enter=SetUserQueryAction('')
                ))

            return RenderResultListAction(items)

        # Fallback
        items.append(ExtensionSmallResultItem(
            icon='images/error.png',
            name='Unrecognized event data',
            on_enter=CopyToClipboardAction(str(data))
        ))
        return RenderResultListAction(items)


class KeywordQueryEventListener(EventListener):
    def __help(self):
        return [
            ExtensionSmallResultItem(
                icon='images/info.png',
                name='s <pattern> — fast indexed search (plocate)',
                on_enter=SetUserQueryAction('s ')
            ),
            ExtensionSmallResultItem(
                icon='images/info.png',
                name='s hw <pattern> — live search on mounted drives (/run/media, /media, /mnt)',
                on_enter=SetUserQueryAction('s hw ')
            ),
            ExtensionSmallResultItem(
                icon='images/info.png',
                name='s r <locate-args> — raw plocate/locate mode (regex, case-sensitive)',
                on_enter=SetUserQueryAction('s r ')
            )
        ]

    def on_event(self, event, extension):
        arg = event.get_argument()
        items = []

        if not arg or not arg.strip():
            items = self.__help()
        else:
            try:
                results = locator.run(arg)

                per_page = locator.limit or 10
                page = 0
                start = page * per_page
                end = start + per_page
                page_slice = results[start:end]

                for file in page_slice:
                    items.append(ExtensionSmallResultItem(
                        icon='images/ok.png',
                        name=file,
                        on_enter=OpenAction(file),
                        on_alt_enter=ExtensionCustomAction(results, keep_app_open=True)
                    ))

                if end < len(results):
                    payload = {
                        'type': 'page',
                        'results': results,
                        'page': page + 1,
                        'per_page': per_page
                    }
                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"More results ({len(results) - end} remaining) — press Enter to load",
                        on_enter=ExtensionCustomAction(payload, keep_app_open=True)
                    ))
                else:
                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"Found {len(results)} result(s)",
                        on_enter=SetUserQueryAction('')
                    ))

            except Exception as e:
                items = [ExtensionSmallResultItem(
                    icon='images/error.png',
                    name=str(e),
                    on_enter=CopyToClipboardAction(str(e))
                )]

        return RenderResultListAction(items)


if __name__ == '__main__':
    SearchFileExtension().run()
