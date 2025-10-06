from typing import Protocol, Any

from textual.binding import Binding
from textual.css.query import DOMQuery, NoMatches
from textual.geometry import Region
from textual.widget import Widget
from textual.widgets import Collapsible, TabbedContent

class FocusableScreen(Protocol):
    focused: Widget
    navigation_map: dict[str, dict[str, str]]
    size: property
    def query_one(self, query: str, **kwargs: Any) -> Widget: ...
    def query(self, selector: str | None = None) -> DOMQuery[Widget]: ...
    def notify(self, message: str, **kwargs: Any) -> None: ...
    def _find_next_focus(self, current: Widget, direction: str) -> Widget | None: ...

class NavigationMixin:
    BINDINGS = [
        Binding("up", "focus_move('up')", show=False),
        Binding("down", "focus_move('down')", show=False),
        Binding("left", "focus_move('left')", show=False),
        Binding("right", "focus_move('right')", show=False),
    ]

    def _find_next_focus(self: FocusableScreen, current: Widget, direction: str) -> Widget | None:
        """Find the next focusable widget in the given direction."""
        # --- Helper: compute projection region ---
        def compute_projection(focused_region: Region, direction: str, expanded: bool = False) -> Region:
            if not expanded:
                if direction == "up":
                    return Region(focused_region.x, 0, focused_region.width, focused_region.y)
                elif direction == "down":
                    return Region(focused_region.x, focused_region.y, focused_region.width, self.size.height - focused_region.y)
                elif direction == "left":
                    return Region(0, focused_region.y, focused_region.x - 1, focused_region.height)
                elif direction == "right":
                    return Region(focused_region.right, focused_region.y, self.size.width - focused_region.right, focused_region.height)
            else:
                expanded_width = focused_region.width * 2
                expanded_x = focused_region.x - focused_region.width // 2
                if direction == "up":
                    return Region(expanded_x, 0, expanded_width, focused_region.y - 1)
                elif direction == "down":
                    return Region(expanded_x, focused_region.bottom, expanded_width, self.size.height - focused_region.bottom)
                elif direction == "left":
                    return Region(0, 0, focused_region.x - 1, self.size.height)
                elif direction == "right":
                    return Region(focused_region.right, 0, self.size.width - focused_region.right, self.size.height)
            return focused_region  # fallback

        # --- Helper: filter candidates ---
        def is_candidate(w: Widget) -> bool:
            if w == current or not w.region.intersection(proj_region):
                return False
            try:
                if direction == "down" and current in w.query_one("Contents").children:
                    return False
            except NoMatches:
                pass
            if current in w.children:
                return False
            return True

        # --- Helper: collect candidates ---
        def get_candidates() -> list[Widget]:
            result = []
            for w in self.query(".focusable"):
                if isinstance(w, TabbedContent):
                    w = w.query_one("ContentTabs")
                if not is_candidate(w):
                    continue
                if isinstance(w, Collapsible):
                    title = w.query_one("CollapsibleTitle")
                    if title:
                        result.append(title)
                else:
                    result.append(w)
            return result

        # --- Start main logic ---
        focused_region = current.region
        proj_region = compute_projection(focused_region, direction)
        candidates = get_candidates()

        # If nothing intersects, expand projection
        if not candidates:
            proj_region = compute_projection(focused_region, direction, expanded=True)
            candidates = get_candidates()

        # --- Pick nearest candidate ---
        if candidates:
            def distance(w: Widget) -> tuple[float, float]:
                fx, fy = focused_region.center
                tx = min(max(fx, w.region.x), w.region.right)
                ty = min(max(fy, w.region.y), w.region.bottom)
                dx = abs(tx - fx)
                dy = abs(ty - fy)
                return dy, dx

            return min(candidates, key=distance)

        return None

    def action_focus_move(self: FocusableScreen, direction: str):
        focused = self.focused
        if focused and isinstance(focused.parent, Collapsible):
            focused = focused.parent
        if not focused:
            return
        try:
            next_widget = self._find_next_focus(focused, direction)
            if next_widget:
                next_widget.focus()
        except Exception as e:
            self.notify(f"Failed to move focus. {e}", severity="error", timeout=5)
