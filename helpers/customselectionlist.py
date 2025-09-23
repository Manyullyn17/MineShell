from textual.events import Key
from textual.widgets import SelectionList

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
