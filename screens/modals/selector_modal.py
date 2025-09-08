from packaging.version import Version, InvalidVersion

from textual import work, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import Resize
from textual.widgets import DataTable

from screens.modals import FilterModal
from helpers import CustomModal

class SelectorModal(CustomModal[str]):
    """A reusable modal that can show a list of values with optional extra info."""
    CSS_PATH = 'styles/selector_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
            Binding('f', 'filter', 'Filter', show=True),
            Binding('r', 'reset', 'Reset', show=True),
        ]

    def __init__(self, title: str, choices: list[dict[str, str | list[str]]], return_field: str='', hide_return_field: bool=False,
                 show_filter: bool = True, filter_columns: list[str] | None = None, sort_column: str | None = None, sort_reverse: bool = True):
        super().__init__()
        self.title_txt = title
        self.subtitle_txt = 'f to filter, r to reset' if show_filter else ''
        self.choices = choices
        self.return_field: str = return_field if return_field else next(iter(choices[0]))
        self.hide_return_field = hide_return_field
        self.filter_columns = filter_columns
        self.show_filter = show_filter
        self.sort_column = sort_column
        self.sort_reverse = sort_reverse
        self.min_width = max(len(title) + 6, len(self.subtitle_txt if show_filter else '') + 4)

    def compose(self) -> ComposeResult:
        # Determine the maximum number of columns in choices
        self.max_columns = max(len(choice) for choice in self.choices)

        # Create the table
        self.table = DataTable(id="selector-list", cursor_type='row', zebra_stripes=True)
        # Add columns dynamically
        for column in self.choices[0].keys():
            if self.hide_return_field and column == self.return_field:
                self.table.add_column(column.replace('_', ' ').title(), key=column, width=0)
            else:
                self.table.add_column(column.replace('_', ' ').title(), key=column)

        # Add rows
        self.load_table(self.choices)

        self.table.border_title = self.title_txt
        self.table.border_subtitle = self.subtitle_txt
        yield self.table

    def on_mount(self):
        self.length = 4 + sum((col.content_width if col.width != 0 else 0) + 2 for col in self.table.columns.values())

    @on(Resize)
    def on_resize(self, event: Resize):
        self.table.styles.width = min(int(self.size.width * 0.8), max(self.min_width, self.length))
        self.table.styles.height = min(int(self.size.height * 0.8), len(self.table.rows) + 4)

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

    @work
    async def load_table(self, data: list[dict[str, str | list[str]]]):
        self.table.loading = True
        for choice in data:
            row = [
                ', '.join(cell) if isinstance(cell, list) else cell
                for cell in choice.values()
            ]
            self.table.add_row(*row, key=str(choice[self.return_field]))
        if self.sort_column:
            # - always uses version sort key if sort_column is provided, could use general purpose sort key
            def version_key(v: str):
                try:
                    return Version(v)
                except InvalidVersion:
                    return v.lower()
            self.table.sort(self.sort_column, key=lambda r: version_key(r), reverse=self.sort_reverse)
        self.table.loading = False

