from textual.widgets import DataTable
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.binding import Binding
from screens.filter_modal import FilterModal

class SelectorModal(ModalScreen[str]):
    """A reusable modal that can show a list of values with optional extra info."""
    CSS_PATH = 'styles/selector_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
            Binding('f', 'filter', 'Filter', show=True),
            Binding('r', 'reset', 'Reset', show=True),
        ]

    def __init__(self, title: str, choices: list[dict[str, str | list[str]]], return_field: str='', hide_return_field: bool=False, show_filter: bool = True, filter_columns: list[str] | None = None):
        super().__init__()
        self.title_txt = title
        self.subtitle_txt = 'f to filter, r to reset' if show_filter else ''
        self.choices = choices
        self.return_field: str = return_field if return_field else next(iter(choices[0]))
        self.hide_return_field = hide_return_field
        self.filter_columns = filter_columns

        self.show_filter = show_filter

    def compose(self) -> ComposeResult:
        # Determine the maximum number of columns in choices
        self.max_columns = max(len(choice) for choice in self.choices)

        # Create the table
        self.table = DataTable(id="selector-list", cursor_type='row', zebra_stripes=True)
        # Add columns dynamically
        for column in self.choices[0].keys():
            if self.hide_return_field and column == self.return_field:
                self.table.add_column(column.replace('_', ' ').title(), width=0)
            else:
                self.table.add_column(column.replace('_', ' ').title())

        # Add rows
        self.load_table(self.choices)

        self.table.border_title = self.title_txt
        self.table.border_subtitle = self.subtitle_txt
        yield self.table

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        selected_row = event.row_key.value
        self.dismiss(str(selected_row))

    def action_back(self):
        self.dismiss()

    def action_filter(self):
        def filter_chosen(filter: dict | None) -> None:
            if filter:
                formatted_filters = ' | '.join(
                    f"{col.title()}: {', '.join(val) if isinstance(val, list) else val.strip('[]').replace('\'','')}" 
                    for col, val in filter.items()
                )
                self.table.border_title = f'{self.title_txt} (Filter: {formatted_filters})'
                self.table.clear()

                filtered_data = [
                    row for row in self.choices
                    if all(
                        any(val in row[col] if isinstance(row[col], list) else val == row[col] for val in values)
                        for col, values in filter.items()
                    )
                ]

                self.load_table(filtered_data)
            else:
                self.table.border_title = self.title_txt
                self.table.clear()
                self.load_table(self.choices)
        
        self.app.push_screen(FilterModal(self.choices, self.filter_columns), filter_chosen)
        return

    def action_reset(self):
        self.table.border_title = self.title_txt
        self.table.clear()
        self.load_table(self.choices)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == 'filter' and not self.show_filter:
            return False
        if action == 'reset' and not self.show_filter:
            return False
        return super().check_action(action, parameters)

    def load_table(self, data: list[dict[str, str | list[str]]]):
        for choice in data:
            row = [
                ', '.join(cell) if isinstance(cell, list) else cell
                for cell in choice.values()
            ]
            self.table.add_row(*row, key=str(choice[self.return_field]))
