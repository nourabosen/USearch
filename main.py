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
        limit = event.preferences.get('limit')
        if limit is not None:
            locator.set_limit(limit)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        items = []

        # Expecting: {'results': [...], 'page': N, 'per_page': M}
        if isinstance(data, dict) and 'results' in data:
            results = data['results']
            page = data.get('page', 0)
            per_page = data.get('per_page', 10)
            start = page * per_page
            end = start + per_page
            page_results = results[start:end]

            for file in page_results:
                items.append(ExtensionSmallResultItem(
                    icon='images/ok.png',
                    name=file,
                    on_enter=OpenAction(file),
                    on_alt_enter=CopyToClipboardAction(file)
                ))

            # "More results" item
            if end < len(results):
                next_payload = {
                    'results': results,
                    'page': page + 1,
                    'per_page': per_page
                }
                items.append(ExtensionSmallResultItem(
                    icon='images/info.png',
                    name=f"More results ({len(results) - end} remaining) — press Enter",
                    on_enter=ExtensionCustomAction(next_payload, keep_app_open=True)
                ))
            else:
                items.append(ExtensionSmallResultItem(
                    icon='images/info.png',
                    name=f"End of results — {len(results)} total",
                    on_enter=SetUserQueryAction('')
                ))

        else:
            # Fallback: treat as raw list (e.g., from old alt-enter)
            results = data if isinstance(data, list) else []
            for file in results[:10]:
                items.append(ExtensionSmallResultItem(
                    icon='images/copy.png',
                    name=file,
                    on_enter=CopyToClipboardAction(file)
                ))

        return RenderResultListAction(items)


class KeywordQueryEventListener(EventListener):
    def __help(self):
        return [
            ExtensionSmallResultItem(
                icon='images/info.png',
                name='s <pattern> — fast indexed + hardware search',
                on_enter=SetUserQueryAction('s ')
            ),
            ExtensionSmallResultItem(
                icon='images/info.png',
                name='s hw <pattern> — search only mounted drives (/run/media, /media, /mnt)',
                on_enter=SetUserQueryAction('s hw ')
            ),
            ExtensionSmallResultItem(
                icon='images/info.png',
                name='s r <args> — raw plocate/locate mode (regex, case-sensitive)',
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
                # Get FULL result list from locator (no truncation)
                results = locator.run(arg)

                # Apply limit from preferences (default to 10 if not set)
                per_page = locator.limit if locator.limit and locator.limit > 0 else 10
                total = len(results)

                # Show first page
                page_results = results[:per_page]
                for file in page_results:
                    items.append(ExtensionSmallResultItem(
                        icon='images/ok.png',
                        name=file,
                        on_enter=OpenAction(file),
                        on_alt_enter=CopyToClipboardAction(file)
                    ))

                # Add "More results" if needed
                if total > per_page:
                    payload = {
                        'results': results,
                        'page': 1,
                        'per_page': per_page
                    }
                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"More results ({total - per_page} remaining) — press Enter",
                        on_enter=ExtensionCustomAction(payload, keep_app_open=True)
                    ))
                else:
                    items.append(ExtensionSmallResultItem(
                        icon='images/info.png',
                        name=f"Found {total} result(s)",
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
