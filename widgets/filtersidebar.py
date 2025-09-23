from typing import Callable

from textual.css.query import NoMatches
from textual.message import Message
from textual.widgets import Collapsible, SelectionList

from helpers import CustomVerticalScroll, CustomSelectionList

class FilterSidebar(CustomVerticalScroll):
    DEFAULT_CSS = """
    FilterSidebar {
        .collapsible {
            Contents {
                padding: 1 1 0 0;
            }
            margin: 0 1 0 0;
        }
        .selectionlist {
            max-height: 20;
            .selection-list--button-selected {
                background: $surface-lighten-1;
            }
            width: 1fr;
        }
    }
    """

    class FilterChanged(Message):
        """Posted when a filter changes."""
        def __init__(self, sender: "FilterSidebar", event: SelectionList.SelectedChanged) -> None:
            super().__init__()
            self.sender = sender
            self.filter = event.selection_list.id
            self.selected = event.selection_list.selected

    def on_selection_list_selected_changed(self, event: SelectionList.SelectedChanged) -> None:
        self.post_message(self.FilterChanged(self, event))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._categories: dict[str, Collapsible] = {}
        self._default_filters: dict[str, list[str]] = {}

    def add_category(self, name: str, filter_name: str | None = None,collapsed: bool = True, wait_for_refresh_cb: Callable | None = None) -> bool:
        """
            Add a new filter category with no options yet.
            Returns:
                bool\n
                True if successful.\n
                False if already exists.
        """
        if name.lower() in self._categories:
            return False
        
        selection_list = CustomSelectionList(compact=True, id=filter_name or name, classes=f"{' '.join(self.classes)} selectionlist focusable")
        collapsible = Collapsible(
            selection_list,
            title=name.title(),
            collapsed=collapsed,
            classes=f"{' '.join(self.classes)} collapsible focusable",
        )
        self._categories[name.lower()] = collapsible
        self.mount(collapsible)

        if wait_for_refresh_cb:
            return self.call_after_refresh(lambda: wait_for_refresh_cb(collapsible))
        return True

    def add_categories(self, categories: list[tuple[str, str] | str]) -> bool:
        """Add multiple categories."""
        for category in categories:
            display = category[0] if isinstance(category, tuple) else category
            ret_val = category[1] if isinstance(category, tuple) else category
            if not self.add_category(display, ret_val):
                return False
        return True

    def add_options(self, name: str, options: list[str], selected: list[str] = []) -> bool:
        """Add options to an existing category (mounts if not present)."""
        key = name.lower()
        def _add_to_selectionlist(collapsible: Collapsible) -> bool:
            """Add options to selectionlist."""
            try:
                selection_list = collapsible.query_one(SelectionList)
            except NoMatches:
                return False
            
            self._default_filters[key] = selected
            for opt in options:
                selection_list.add_option((opt.title(), opt, opt in selected))
            
            return True

        if key not in self._categories:
            # auto-create if category not there
            return self.add_category(key, wait_for_refresh_cb=_add_to_selectionlist)
        else:
            collapsible = self._categories[key]
            return _add_to_selectionlist(collapsible)

    def get_selected_filters(self) -> dict[str, list[str]]:
        """Get currently selected filters."""
        selected: dict[str, list[str]] = {}
        for name, collapsible in self._categories.items():
            try:
                selection_list = collapsible.query_one(SelectionList)
            except NoMatches:
                continue
            if selection_list.selected:
                selected[name] = selection_list.selected
        return selected
    
    def reset_filters(self):
        for name, collapsible in self._categories.items():
            try:
                selection_list = collapsible.query_one(SelectionList)
            except NoMatches:
                continue
            selection_list.deselect_all()
            if self._default_filters and name in self._default_filters.keys():
                for opt in self._default_filters[name]:
                    selection_list.select(opt)

    def clear_options(self, name: str) -> bool:
        """Clear all options for a given filter category."""
        key = name.lower()
        if key not in self._categories:
            return False

        try:
            selection_list = self._categories[key].query_one(SelectionList)
        except NoMatches:
            return False

        selection_list.clear_options()
        if key in self._default_filters:
            del self._default_filters[key]

        return True
