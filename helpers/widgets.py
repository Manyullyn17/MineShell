from typing import TypeVar, Protocol, Any

from textual import on
from textual.binding import Binding
from textual.css.query import DOMQuery
from textual.events import MouseDown
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Select, Input, DataTable
class CustomSelect(Select):
    def on_key(self, event):
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
    def on_key(self, event):
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

    def on_key(self, event):
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

    # def action_focus_move(self: FocusableScreen, direction: str):
    #     focused = self.focused
    #     if not focused or not focused.id:
    #         return
    #     try:
    #         next_id = self.navigation_map.get(focused.id, {}).get(direction)
    #         if next_id:
    #             next_widget = self.query_one(f'#{next_id}')
    #             next_widget.focus()
    #     except Exception as e:
    #         self.notify(f"Failed to move focus. {e}", severity="error", timeout=5)

    def _find_next_focus(self: FocusableScreen, current: Widget, direction: str) -> Widget | None:
        current_region = current.region
        current_cx = current_region.x + current_region.width // 2
        current_cy = current_region.y + current_region.height // 2
        current_left = current_region.x
        current_right = current_region.right
        current_top = current_region.y
        current_bottom = current_region.bottom

        candidates = [w for w in self.query("*") if w.can_focus and w.id != current.id]

        def score(widget: Widget) -> float:
            r = widget.region
            w_left = r.x
            w_right = r.right
            w_top = r.y
            w_bottom = r.bottom
            dx = dy = 0

            # - make it prioritize the direction navigation is heading in
            if direction == "left" and w_right <= current_left:
                dx = current_left - w_right
                # vertical distance: distance from current top/bottom to closest candidate edge
                dy = max(0, current_top - w_bottom, w_top - current_bottom)

            if direction == "right" and w_left >= current_right:
                dx = w_left - current_right
                dy = max(0, current_top - w_bottom, w_top - current_bottom)

            if direction == "up" and w_bottom <= current_top:
                dy = current_top - w_bottom
                dx = max(0, current_left - w_right, w_left - current_right)

            if direction == "down" and w_top >= current_bottom:
                dy = w_top - current_bottom
                dx = max(0, current_left - w_right, w_left - current_right)

            if dx or dy:
                return dx + dy*2

            return float("inf")  # not in the correct direction

        scored = [(score(w), w) for w in candidates if score(w) < float("inf")]
        if not scored:
            return None

        return min(scored, key=lambda sw: sw[0])[1]

    def action_focus_move(self: FocusableScreen, direction: str):
        focused = self.focused
        if not focused or not focused.id:
            return
        try:
            next_widget = self._find_next_focus(focused, direction)
            if next_widget:
                next_widget.focus()
        except Exception as e:
            self.notify(f"Failed to move focus. {e}", severity="error", timeout=5)
