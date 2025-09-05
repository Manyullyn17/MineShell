from textual.widgets import Button, Static, Checkbox
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from helpers import CustomSelect, CustomModal

class SortModal(CustomModal[tuple[str, bool]]):
    """A reusable modal to select values to sort by."""
    CSS_PATH = 'styles/sort_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'esc', show=False),
            Binding('up', "focus_move('up')", show=False),
            Binding('down', "focus_move('down')", show=False),
            Binding('left', "focus_move('left')", show=False),
            Binding('right', "focus_move('right')", show=False),
        ]
    
    navigation_map = {
        "sort-select":      {"left": "",                         "up": "",  "down": "modlist-table", "right": "modlist-filter-button"},
        "sort-reverse":     {"left": "modlist-search",           "up": "",  "down": "modlist-table", "right": "modlist-sort-button"},
        "sort-back-button": {"left": "modlist-filter-button",    "up": "",  "down": "modlist-table", "right": "modlist-update-button"},
        "sort-done-button": {"left": "modlist-sort-button",      "up": "",  "down": "modlist-table", "right": "modlist-add-mod-button"},
    }

    def __init__(self, sortable_columns:list[str]):
        super().__init__()
        self.sortable_columns = sortable_columns

    def compose(self) -> ComposeResult:
        self.grid = Grid(id='sort-grid')

        with self.grid:
            yield Static('Column: ', classes='sort text')
            self.sort_select = CustomSelect.from_values(self.sortable_columns, id='sort-select', classes='sort select', allow_blank=False)
            yield self.sort_select
            self.reverse = Checkbox(label='Reverse', id='sort-reverse', classes='sort checkbox')
            yield self.reverse
            yield Button('Back', id='sort-back-button', classes='sort button')
            yield Button('Done', id='sort-done-button', classes='sort button')

        self.grid.border_title = 'Sort Table'
        
    def on_mount(self):
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'sort-back-button':
                self.action_back()
            case 'sort-done-button':
                self.action_done()

    def action_focus_move(self, direction: str):
        focused = self.focused
        if not focused or not focused.id:
            return
        try:
            next_id = self.navigation_map.get(focused.id, {}).get(direction)
            if next_id:
                next_widget = self.query_one(f'#{next_id}')
                next_widget.focus()
        except Exception as e:
            self.notify(f"Failed to move focus. {e}", severity='error', timeout=5)

    def action_back(self):
        self.dismiss()

    def action_done(self):
        self.dismiss((str(self.sort_select.value), self.reverse.value))

