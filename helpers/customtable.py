from textual.binding import Binding
from textual.events import Key
from textual.widgets import DataTable

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
