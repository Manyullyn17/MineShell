from textual.events import Key
from textual.widgets import Input

class CustomInput(Input):
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
