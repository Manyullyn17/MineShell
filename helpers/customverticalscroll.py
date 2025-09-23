from textual.containers import VerticalScroll
from textual.events import Key

class CustomVerticalScroll(VerticalScroll):
    allow_scroll = False

    def __init__(self, *args, allow_scroll: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_scroll = allow_scroll

    def on_key(self, event: Key):
        """Override to make up/down move focus instead of scrolling."""
        if (not self.allow_scroll and event.key in ("up", "down")) or \
            (self.allow_scroll and ((event.key == "up" and self.scroll_y == 0) or
            (event.key == "down" and self.scroll_y == self.max_scroll_y))) or \
            event.key in ("left", "right"):
            # Call the screen's focus movement
            screen = self.app.screen
            if hasattr(screen, "action_focus_move"):
                getattr(screen, "action_focus_move")(event.key)
            event.stop()
            return
        # Fallback to normal VerticalScroll behavior
        return super()._on_key(event)
