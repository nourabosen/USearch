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
        hint_str='locate -i'
        query_str='s r '
        items.append(ExtensionSmallResultItem(icon='images/info.png',
                                                name=hint_str,
                                                on_enter=SetUserQueryAction(
                                                    query_str)
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
                alt_action = ExtensionCustomAction(results, True)
                for file in results:
                    items.append(ExtensionSmallResultItem(icon='images/ok.png',
                        name=file, 
                        on_enter=OpenAction(file),
                        on_alt_enter=alt_action))
            except Exception as e:
                error_info = str(e)
                items = [ExtensionSmallResultItem(icon='images/error.png',
                                                name=error_info,
                                                on_enter=CopyToClipboardAction(error_info))]
        
        return RenderResultListAction(items)

if __name__ == '__main__':
    SearchFileExtension().run()
