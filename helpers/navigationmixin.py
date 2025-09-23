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
        def get_candidates(self) -> list[Widget]:
            candidates = []
            for w in self.query('.focusable'):
                if isinstance(w, TabbedContent):
                    # if TabbedContent, use ContentTabs for region
                    w = w.query_one('ContentTabs')
                # if same widget or not in region, skip
                if w == current or not w.region.intersection(proj_region):
                    continue
                try:
                    # ignore collapsible if inside and pressing down to get out
                    if current in w.query_one('Contents').children and direction == 'down':
                        continue
                except NoMatches:
                    pass
                if current in w.children:
                    continue
                if isinstance(w, Collapsible):
                    # find the CollapsibleTitle child of the collapsible
                    title = w.query_one('CollapsibleTitle')
                    if title:
                        candidates.append(title)
                else:
                    candidates.append(w)
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
