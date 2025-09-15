from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.widgets import Button, Static, Checkbox

from helpers import CustomSelect, CustomModal, FocusNavigationMixin

class SortModal(FocusNavigationMixin, CustomModal[tuple[str, bool]]):
    """A reusable modal to select values to sort by."""
    CSS_PATH = 'styles/sort_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'esc', show=False),
        ] + FocusNavigationMixin.BINDINGS

    def __init__(self, sortable_columns:list[str]):
        super().__init__()
        self.sortable_columns = sortable_columns

    def compose(self) -> ComposeResult:
        self.grid = Grid(id='sort-grid')

        with self.grid:
            yield Static('Column: ', classes='sort text')
            self.sort_select = CustomSelect.from_values(self.sortable_columns, id='sort-select', classes='focusable sort select', allow_blank=False)
            yield self.sort_select
            self.reverse = Checkbox(label='Reverse', id='sort-reverse', classes='focusable sort checkbox')
            yield self.reverse
            yield Button('Back', id='sort-back-button', classes='focusable sort button')
            yield Button('Done', id='sort-done-button', classes='focusable sort button')

        self.grid.border_title = 'Sort Table'
        
    def on_mount(self):
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'sort-back-button':
                self.action_back()
            case 'sort-done-button':
                self.action_done()

    def action_back(self):
        self.dismiss()

    def action_done(self):
        self.dismiss((str(self.sort_select.value), self.reverse.value))

