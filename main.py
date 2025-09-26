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
        super().__init__()
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
        locator.set_limit(event.preferences.get('limit'))

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        results = event.get_data()
        items = []
        for f in (results or [])[:10]:
            items.append(ExtensionSmallResultItem(
                icon='images/copy.png',
                name=f,
                on_enter=CopyToClipboardAction(f)
            ))
        return RenderResultListAction(items)

class KeywordQueryEventListener(EventListener):
    def __help(self):
        return [
            ExtensionSmallResultItem(
                icon='images/info.png',
                name='s <file> — search everywhere (indexed + USB drives)',
                on_enter=SetUserQueryAction('s ')
            ),
            ExtensionSmallResultItem(
                icon='images/info.png',
                name='s hw <file> — search only USB/external drives',
                on_enter=SetUserQueryAction('s hw ')
            ),
            ExtensionSmallResultItem(
                icon='images/info.png',
                name='s r <args> — raw locate mode',
                on_enter=SetUserQueryAction('s r ')
            )
        ]

    def on_event(self, event, extension):
        arg = event.get_argument()
        if not arg or not arg.strip():
            return RenderResultListAction(self.__help())

        try:
            results = locator.run(arg)
            # Apply limit from preferences (default 10)
            limit = int(locator.limit) if locator.limit and str(locator.limit).isdigit() else 10
            display_results = results[:limit]

            items = []
            for file in display_results:
                items.append(ExtensionSmallResultItem(
                    icon='images/ok.png',
                    name=file,
                    on_enter=OpenAction(file),
                    on_alt_enter=ExtensionCustomAction(results, keep_app_open=True)
                ))

            if not results:
                items.append(ExtensionSmallResultItem(
                    icon='images/info.png',
                    name="No results found",
                    on_enter=SetUserQueryAction('')
                ))

            return RenderResultListAction(items)

        except Exception as e:
            return RenderResultListAction([
                ExtensionSmallResultItem(
                    icon='images/error.png',
                    name=str(e),
                    on_enter=CopyToClipboardAction(str(e))
                )
            ])
