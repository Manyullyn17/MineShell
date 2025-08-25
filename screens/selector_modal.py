from textual.widgets import DataTable, Label
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.containers import Grid

class SelectorModal(ModalScreen[str]):
    """A reusable modal that can show a list of values with optional extra info."""
    CSS_PATH = 'styles/selector_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
        ]

    def __init__(self, title: str, choices: list[list[str] | str], columns: list[str], height: int=12, width: int=40, return_field: str='', hide_return_field: bool=False):
        super().__init__()
        self.title = title
        # Normalize choices: make sure every item is a list
        self.choices = [c if isinstance(c, list) else [c] for c in choices]
        self.columns = columns
        self.height = height
        self.width = width
        self.return_field = return_field
        self.hide_return_field = hide_return_field

        self.return_index = 0
        if return_field and return_field in columns:
            self.return_index = columns.index(return_field)

    def compose(self) -> ComposeResult:
        # Determine the maximum number of columns in choices
        max_columns = max(len(choice) for choice in self.choices)

        # Create the table
        table = DataTable(id="selector-list", cursor_type='row', zebra_stripes=True)
        # Add columns dynamically
        for i in range(max_columns):
            col_name = self.columns[i] if i < len(self.columns) else ''
            if self.hide_return_field and i == self.return_index:
                table.add_column(col_name, width=0)
            else:
                table.add_column(col_name)

        # Add rows
        for choice in self.choices:
            # Fill missing columns with empty strings
            row = choice + [""] * (max_columns - len(choice))
            table.add_row(*row, key=choice[self.return_index])

        table.border_title = self.title
        yield table

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        selected_row = event.row_key.value
        self.dismiss(str(selected_row))

    def action_back(self):
        self.dismiss()
