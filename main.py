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

# Global locator instance
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
        elif event.id == 'find_timeout':
            try:
                locator.find_timeout = int(event.new_value)
            except ValueError:
                pass

class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        # Set initial preferences
        locator.set_limit(event.preferences.get('limit', 50))
        try:
            locator.find_timeout = int(event.preferences.get('find_timeout', 10))
        except ValueError:
            locator.find_timeout = 10

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
                    name=f"Copy path: {f}",
                    description=f,
                    on_enter=CopyToClipboardAction(f)
                ))
            return RenderResultListAction(items)

        # Paging
        if isinstance(data, dict) and data.get('type') == 'page':
            results = data.get('results', [])
            page = int(data.get('page', 0))
            per_page = int(data.get('per_page', 50))
            start = page * per_page
            end = start + per_page
            slice_results = results[start:end]

            for file in slice_results:
                items.append(ExtensionSmallResultItem(
                    icon='images/ok.png',
                    name=file,
                    description="Press Enter to open, Alt+Enter to see all results",
                    on_enter=OpenAction(file),
                    on_alt_enter=ExtensionCustomAction(results, True)
                ))

            if end < len(results):
                more_payload = {'type': 'page', 'results': results, 'page': page + 1, 'per_page': per_page}
                items.append(ExtensionSmallResultItem(
                    icon='images/more.png',
                    name=f"Load more results ({len(results) - end} remaining)",
                    description="Press Enter to load next page",
                    on_enter=ExtensionCustomAction(more_payload, True)
                ))
            else:
                items.append(ExtensionSmallResultItem(
                    icon='images/info.png',
                    name=f"Search complete - {len(results)} results found",
                    description="All results have been displayed",
                    on_enter=SetUserQueryAction('s ')
                ))

            return RenderResultListAction(items)

        # Fallback error
        items.append(ExtensionSmallResultItem(
            icon='images/error.png',
            name='Unrecognized event data',
            description=str(data)[:100] + '...' if len(str(data)) > 100 else str(data),
            on_enter=CopyToClipboardAction(str(data))
        ))
        return RenderResultListAction(items)

class KeywordQueryEventListener(EventListener):
    def __help(self):
        items = []
        items.append(ExtensionSmallResultItem(
            icon='images/info.png',
            name='Normal search: s <pattern>',
            description='Fast indexed search (plocate) + hardware drives',
            on_enter=SetUserQueryAction('s ')
        ))
        items.append(ExtensionSmallResultItem(
            icon='images/hardware.png',
            name='Hardware-only search: s hw <pattern>',
            description='Live search on mounted media (/run/media, /media, /mnt)',
            on_enter=SetUserQueryAction('s hw ')
        ))
        items.append(ExtensionSmallResultItem(
            icon='images/raw.png',
            name='Raw locate search: s r <locate-args>',
            description='Raw plocate/locate arguments (regex, case-sensitive, etc.)',
            on_enter=SetUserQueryAction('s r ')
        ))
        items.append(ExtensionSmallResultItem(
            icon='images/settings.png',
            name='Extension settings',
            description='Configure result limit and timeout in Ulauncher preferences',
            on_enter=SetUserQueryAction('ulauncher-preferences')
        ))
        return items

    def _create_result_items(self, results, query):
        """Create result items from search results with pagination."""
        items = []
        
        if not results:
            items.append(ExtensionSmallResultItem(
                icon='images/warning.png',
                name='No results found',
                description='Try a different search term or check the debug log',
                on_enter=SetUserQueryAction('s ')
            ))
            return items

        # Show first page
        per_page = locator.limit or 50
        page = 0
        start = page * per_page
        end = start + per_page
        page_slice = results[start:end]

        for file in page_slice:
            # Truncate very long filenames for display
            display_name = file if len(file) <= 80 else f"{file[:77]}..."
            items.append(ExtensionSmallResultItem(
                icon='images/file.png',
                name=display_name,
                description=file,  # Full path in description
                on_enter=OpenAction(file),
                on_alt_enter=ExtensionCustomAction(results, True)
            ))

        if end < len(results):
            payload = {'type': 'page', 'results': results, 'page': page + 1, 'per_page': per_page}
            items.append(ExtensionSmallResultItem(
                icon='images/more.png',
                name=f"Load more results ({len(results) - end} remaining)",
                description=f"Page {page + 2} - Press Enter to continue",
                on_enter=ExtensionCustomAction(payload, True)
            ))
        else:
            items.append(ExtensionSmallResultItem(
                icon='images/success.png',
                name=f"Search complete - {len(results)} result(s) found",
                description="All results have been displayed",
                on_enter=SetUserQueryAction('s ')
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
                items = self._create_result_items(results, arg)

            except Exception as e:
                error_info = str(e)
                # Log the full error for debugging
                import traceback
                traceback.print_exc()
                
                items = [ExtensionSmallResultItem(
                    icon='images/error.png',
                    name='Search error',
                    description=error_info,
                    on_enter=CopyToClipboardAction(error_info)
                )]
                # Add help items after error
                items.extend(self.__help())

        return RenderResultListAction(items)

if __name__ == '__main__':
    SearchFileExtension().run()
