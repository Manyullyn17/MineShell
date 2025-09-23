from textual.events import Key
from textual.widgets import Select

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
