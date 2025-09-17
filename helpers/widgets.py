from typing import TypeVar, Protocol, Any

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.css.query import DOMQuery, NoMatches
from textual.events import MouseDown, Key
from textual.geometry import Region
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Select, Input, DataTable, Collapsible, SelectionList

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
                self.size.height - focused_region.bottom,
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
        
        # If nothing intersects, expand projection to full row/column
        if not candidates:
            if direction == "up":
                proj_region = Region(
                    0,
                    0,
                    self.size.width,
                    focused_region.y - 1
                )
            elif direction == "down":
                proj_region = Region(
                    0,
                    focused_region.bottom,
                    self.size.width,
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
    def __init__(self, filters: dict[str, list[str]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters = filters

    def compose(self) -> ComposeResult:
        for filter_name, options in self.filters.items():
            selection_list = CustomSelectionList(*[(opt.title(), opt) for opt in options], compact=True, classes='focusable')
            collapsible = Collapsible(selection_list, title=filter_name.title(), collapsed=True, classes='modbrowser filter collapsible focusable')
            yield collapsible

    def get_selected_filters(self) -> dict[str, list[str]]:
        selected: dict[str, list[str]] = {}
        for collapsible in self.query(Collapsible):
            filter_name = collapsible.title.lower()
            try:
                selection_list = collapsible.query_one(SelectionList)
            except NoMatches:
                continue
            selected_options = selection_list.selected
            if selected_options:
                selected[filter_name] = selected_options
        return selected
    
