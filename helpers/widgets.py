from typing import TypeVar, Protocol, Any, Callable

from textual import on
from textual.binding import Binding
from textual.containers import VerticalScroll, Horizontal, VerticalGroup
from textual.css.query import DOMQuery, NoMatches
from textual.events import MouseDown, Key, Enter, Leave, Focus, Blur
from textual.geometry import Region
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Select, Input, DataTable, Collapsible, SelectionList, Static, LoadingIndicator

class CustomSelect(Select):
    def on_key(self, event: Key):
        """Override to prevent up/down from opening the menu."""
        if event.key in ("up", "down") and not self.expanded:
            # Let the default navigation work, but don’t trigger menu opening
            screen = self.app.screen
            if hasattr(screen, "action_focus_move"):
                getattr(screen, "action_focus_move")(event.key)
            event.stop()
            return
        # Fallback to normal Select behavior
        return super()._on_key(event)
    
    def set_value(self, value):
        self.value = value

class SmartInput(Input):
    def on_key(self, event: Key):
        if event.key in ("left", "right"):
            # Determine if we should move focus
            move_focus = (
                (event.key == "left" and self.cursor_at_start) or
                (event.key == "right" and self.cursor_at_end)
            )

            if move_focus:
                # Call the screen's focus movement
                screen = self.app.screen
                if hasattr(screen, "action_focus_move"):
                    getattr(screen, "action_focus_move")(event.key)
                event.stop()
                return

        # fallback to normal Input behavior
        return super()._on_key(event)

class CustomTable(DataTable):
    BINDINGS = [
        Binding(
            "enter,space",
            "show_overlay",
            "Show menu",
            show=False,
        )
    ]

    def on_key(self, event: Key):
        """Override to make up/down move focus if top or bottom row is selected."""
        if event.key in ("up", "down") and self.cursor_type == 'row':
            # Determine if we should move focus
            move_focus = (
                (event.key == "up" and self.cursor_row == 0) or
                (event.key == "down" and self.cursor_row == len(self.rows)-1)
            )

            if move_focus:
                # Call the screen's focus movement
                screen = self.app.screen
                if hasattr(screen, "action_focus_move"):
                    getattr(screen, "action_focus_move")(event.key)
                event.stop()
                return
        if event.key == 'enter':
            super()._post_selected_message()
        # Fallback to normal DataTable behavior
        return super()._on_key(event)

ScreenResultType = TypeVar("ScreenResultType")

class CustomModal(ModalScreen[ScreenResultType]):
    main_widget: Widget | None = None
    allow_click_outside: bool = True  # default behavior

    @on(MouseDown)
    def on_mouse_down(self, event: MouseDown):
        if not self.allow_click_outside:
            return  # ignore clicks outside

        widget = self.get_main_widget()
        if not widget or not widget.styles.height or not widget.styles.width:
            return

        w = widget.styles.width.value or 0
        h = widget.styles.height.value or 0
        if w == 0 or h == 0:
            return

        x, y, width, height = self.find_widget(widget).region
        left = x
        right = x + width - 1
        top = y
        bottom = y + height - 1

        mx, my = event.screen_x, event.screen_y
        if not (left <= mx <= right and top <= my <= bottom):
            self.dismiss()

    def get_main_widget(self) -> Widget | None:
        if self.main_widget:
            return self.main_widget
        
        # pick first non-system child
        for child in self.children:
            if "-textual-system" not in child.classes:
                return child

        return None

class FocusableScreen(Protocol):
    focused: Widget
    navigation_map: dict[str, dict[str, str]]
    size: property
    def query_one(self, query: str, **kwargs: Any) -> Widget: ...
    def query(self, selector: str | None = None) -> DOMQuery[Widget]: ...
    def notify(self, message: str, **kwargs: Any) -> None: ...
    def _find_next_focus(self, current: Widget, direction: str) -> Widget | None: ...

class FocusNavigationMixin:
    BINDINGS = [
        Binding("up", "focus_move('up')", show=False),
        Binding("down", "focus_move('down')", show=False),
        Binding("left", "focus_move('left')", show=False),
        Binding("right", "focus_move('right')", show=False),
    ]

    def _find_next_focus(self: FocusableScreen, current: Widget, direction: str) -> Widget | None:
        def get_candidates(self) -> list[Widget]:
            candidates = []
            for w in self.query('.focusable'):
                # if same widget or not in region, skip
                if w == current or not w.region.intersection(proj_region):
                    continue
                try:
                    # ignore collapsible if inside and pressing down to get out
                    if current in w.query_one('Contents').children and direction == 'down':
                        continue
                except NoMatches:
                    pass
                if w.focusable:
                    candidates.append(w)
                elif isinstance(w, Collapsible):
                    # find the CollapsibleTitle child of the collapsible
                    title = w.query_one('CollapsibleTitle')
                    if title:
                        candidates.append(title)
            return candidates

        # Get focused widget region
        focused_region = current.region

        # Projection rectangle in the moving direction
        proj_region = Region.from_offset(focused_region.offset, focused_region.size)

        # Adjust projection depending on direction
        if direction == "up":
            proj_region = Region(
                focused_region.x,
                0,
                focused_region.width,
                focused_region.y
            )
        elif direction == "down":
            proj_region = Region(
                focused_region.x,
                focused_region.y, # use top edge to allow detection of nested widgets in collapsible
                focused_region.width,
                self.size.height - focused_region.y,
            )
        elif direction == "left":
            proj_region = Region(
                0,
                focused_region.y,
                focused_region.x - 1,
                focused_region.height,
            )
        elif direction == "right":
            proj_region = Region(
                focused_region.right,
                focused_region.y,
                self.size.width - focused_region.right,
                focused_region.height,
            )

        candidates = get_candidates(self)
        
        expanded_width = focused_region.width * 2
        expanded_x = focused_region.x - focused_region.width // 2

        # If nothing intersects, expand projection to full row/column
        if not candidates:
            if direction == "up":
                proj_region = Region(
                    # 0,
                    expanded_x,
                    0,
                    # self.size.width,
                    expanded_width,
                    focused_region.y - 1
                )
            elif direction == "down":
                proj_region = Region(
                    # 0,
                    expanded_x,
                    focused_region.bottom,
                    # self.size.width,
                    expanded_width,
                    self.size.height - focused_region.bottom,
                )
            elif direction == "left":
                proj_region = Region(
                    0,
                    0,
                    focused_region.x - 1,
                    self.size.height,
                )
            elif direction == "right":
                proj_region = Region(
                    focused_region.right,
                    0,
                    self.size.width - focused_region.right,
                    self.size.height,
                )
            candidates = get_candidates(self)

        # Pick the nearest candidate
        if candidates:
            def distance(w: Widget):
                fx, fy = focused_region.center

                # Clamp focus point to widget bounds
                tx = min(max(fx, w.region.x), w.region.right)
                ty = min(max(fy, w.region.y), w.region.bottom)

                dx = abs(tx - fx)
                dy = abs(ty - fy)

                return (dy, dx)

            next_widget = min(candidates, key=distance)
            return next_widget

    def action_focus_move(self: FocusableScreen, direction: str):
        focused = self.focused
        if isinstance(focused.parent, Collapsible):
            focused = focused.parent
        if not focused:
            return
        try:
            next_widget = self._find_next_focus(focused, direction)
            if next_widget:
                next_widget.focus()
        except Exception as e:
            self.notify(f"Failed to move focus. {e}", severity="error", timeout=5)

class CustomVerticalScroll(VerticalScroll):
    def on_key(self, event):
        """Override to make up/down move focus instead of scrolling."""
        if event.key in ("up", "down"):
            # Call the screen's focus movement
            screen = self.app.screen
            if hasattr(screen, "action_focus_move"):
                getattr(screen, "action_focus_move")(event.key)
            event.stop()
            return
        # Fallback to normal VerticalScroll behavior
        return super()._on_key(event)

class CustomSelectionList(SelectionList):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._first_highlighted = False
        self._last_highlighted = False

    def on_key(self, event: Key):
        """Override to make up/down move focus if top or bottom row is selected."""
        if event.key in ("up", "down"):
            # Determine if we should move focus
            move_focus = (
                (event.key == "up" and self._first_highlighted) or
                (event.key == "down" and self._last_highlighted)
            )

            if move_focus:
                # Call the screen's focus movement
                screen = self.app.screen
                if hasattr(screen, "action_focus_move"):
                    getattr(screen, "action_focus_move")(event.key)
            else:
                # do selectionlist movement and prevent other navigation
                match event.key:
                    case 'up':
                        self.action_cursor_up()
                    case 'down':
                        self.action_cursor_down()
            event.stop()
            return
        # Fallback to normal SelectionList behavior
        return super()._on_key(event)
    
    def on_selection_list_selection_highlighted(self, event: SelectionList.SelectionHighlighted):
        idx = event.selection_index
        if idx == 0:
            self._first_highlighted = True
        else:
            self._first_highlighted = False
        if idx == len(self.options) - 1:
            self._last_highlighted = True
        else:
            self._last_highlighted = False

class FilterSidebar(CustomVerticalScroll):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._categories: dict[str, Collapsible] = {}
        self._default_filters: dict[str, list[str]] = {}

    def add_category(self, name: str, collapsed: bool = True, wait_for_refresh_cb: Callable | None = None) -> bool:
        """
            Add a new filter category with no options yet.
            Returns:
                bool\n
                True if successful.\n
                False if already exists.
        """
        if name.lower() in self._categories:
            return False
        
        selection_list = CustomSelectionList(compact=True, classes=f"{' '.join([c for c in self.classes])} selectionlist focusable")
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

    def add_categories(self, categories: list[str]) -> bool:
        """Add multiple categories."""
        for category in categories:
            if not self.add_category(category):
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

class ModCard(Static):
    """A single mod card that displays mod info and is selectable."""
    DEFAULT_CSS = """
    ModCard {
        border: solid $accent-darken-1;
        padding: 1 2 0 2;
        margin: 1;
        background: $surface;
        height: 10;

        .spacer {
            width: 1fr;
        }

        .header {
            height: 2;

            .name {
                width: auto;
                color: $accent-lighten-1;
            }

            .author {
                width: auto;
                color: $foreground-darken-2;
            }

            .downloads {
                width: auto;
            }
        }

        .description {
            height: 1fr;
        }

        .tags {
            .loaders {
                content-align: left middle;
                height: 1fr;
                width: auto;
            }

            .categories {
                content-align: left middle;
                height: 1fr;
                width: auto;
            }
        }
    }

    ModCard.selected {
        border: double $accent-lighten-1;
        background: $boost;
    }

    ModCard.hovered {
        background: $boost;
    }

    ModCard.modcard-loading-indicator {
        background: $panel-darken-1;
        color: $accent;
        height: 1fr;
        width: 1fr;
    }
    """

    class Selected(Message):
        """Posted when the card is clicked/selected."""
        def __init__(self, sender: "ModCard", mod: dict) -> None:
            super().__init__()
            self.mod = mod
            self.sender = sender

    can_focus = True
    is_selected = reactive(False)

    def __init__(self, mod: dict | None = None, loading: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mod = mod or {}
        self.loading_placeholder = loading
        self.classes = "modcard focusable"

    def compose(self):
        if not self.loading_placeholder:
            with Horizontal(classes="modcard header"):
                yield Static(self.mod.get("name", "Unnamed"), classes="modcard header name")
                yield Static(f" by {self.mod.get('author', 'Unknown')}", classes="modcard header author")
                yield Static(classes='modcard header spacer')
                yield Static(f"Downloads: {self.mod.get('downloads', 0)}", classes="modcard header downloads")
            yield Static(self.mod.get("description", ""), classes="modcard description")
            with Horizontal(classes="modcard tags"):
                yield Static(", ".join(self.mod.get("modloader", [])), classes="modcard tags loaders")
                yield Static(classes='modcard tags spacer')
                yield Static(", ".join(self.mod.get("categories", [])), classes="modcard tags categories")
            self.border_subtitle = ", ".join(self.mod.get('type', '')).title()
        else:
            yield LoadingIndicator(classes='modcard-loading-indicator')
            self.disabled = True

    def on_click(self) -> None:
        self.post_message(self.Selected(self, self.mod))

    def on_enter(self, event: Enter) -> None:
        self.set_class(self.is_mouse_over, "hovered")

    def on_leave(self, event: Leave) -> None:
        self.set_class(self.is_mouse_over, "hovered")

    def on_focus(self, event: Focus) -> None:
        self.is_selected = True

    def on_blur(self, event: Blur) -> None:
        self.is_selected = False

    def watch_is_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")

class ModList(CustomVerticalScroll):
    """Container for multiple mod cards."""

    custom_loading = reactive(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cards: list[ModCard] = []
        self.loading_cards: list[ModCard] = []

    def on_mount(self):
        for _ in range(5):
            card = ModCard(loading=True, classes='loading-card')
            self.loading_cards.append(card)
            self.mount(card)

    def set_mods(self, mods: list[dict]):
        self.cards.clear()
        self.remove_children('.card')
        self.add_mods(mods)

    def add_mods(self, mods: list[dict]):
        for mod in mods:
            card = ModCard(mod, classes='card')
            self.cards.append(card)
            self.mount(card)
        self.custom_loading = False

    def on_mod_card_selected(self, event: ModCard.Selected) -> None:
        # Deselect others
        for card in self.cards:
            card.is_selected = False
        event.sender.is_selected = True

    def watch_custom_loading(self, loading: bool) -> None:
        self.scroll_home(animate=False, immediate=True)
        self.disabled = loading
        self.show_cards(loading)

    def show_cards(self, loading: bool = False) -> None:
        if not loading:
            for card in self.loading_cards:
                card.add_class('hidden')
            for card in self.cards:
                card.remove_class('hidden')
        else:
            for card in self.loading_cards:
                card.remove_class('hidden')
            for card in self.cards:
                card.add_class('hidden')

# - make modlist capture modcard event and forward it's own event?
