from packaging.version import Version, InvalidVersion
from typing import Callable, Awaitable, Any, overload

from textual import work, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable

from screens.modals import FilterModal
from helpers import CustomModal, filter_data

class SelectorModal(CustomModal[str | tuple[str, list[dict[str, str | list[str]]]]]):
    """A reusable modal that can show a list of values with optional extra info."""
    CSS_PATH = 'styles/selector_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
            Binding('f', 'filter', 'Filter', show=True),
            Binding('r', 'reset', 'Reset', show=True),
        ]

    @overload
    def __init__(self, title: str,
                 *,
                 choices: list[dict[str, str | list[str]]],
                 return_field: str = '',
                 hide_return_field: bool = False,
                 show_filter: bool = True,
                 filter_columns: list[str] | None = None,
                 sort_column: str | None = None,
                 sort_reverse: bool = True):
        ...

    @overload
    def __init__(self, title: str,
                 *,
                 choices_fn: Callable[..., Awaitable[Any]],
                 choices_fn_args: tuple | None = None,
                 return_field: str = '',
                 hide_return_field: bool = False,
                 show_filter: bool = True,
                 filter_columns: list[str] | None = None,
                 sort_column: str | None = None,
                 sort_reverse: bool = True):
        ...

    def __init__(self, title: str,
                 choices: list[dict[str, str | list[str]]] | None = None,
                 choices_fn: Callable[..., Awaitable[Any]] | None = None,
                 choices_fn_args: tuple | None = None,
                 return_field: str = '',
                 hide_return_field: bool = False,
                 show_filter: bool = True,
                 filter_columns: list[str] | None = None,
                 sort_column: str | None = None,
                 sort_reverse: bool = True):
        super().__init__()

        if choices is None and choices_fn is None:
            raise ValueError("Either 'choices' or 'choices_fn' must be provided.")
        if choices is not None and choices_fn is not None:
            raise ValueError("'choices' and 'choices_fn' are mutually exclusive.")

        self.title_txt = title
        self.subtitle_txt = 'f to filter, r to reset' if show_filter else ''

        self.choices = choices if choices is not None else []
        self.choices_fn = choices_fn
        self.choices_fn_args = choices_fn_args if choices_fn_args is not None else ()
        self.mode = 'choices' if choices is not None else 'choices_fn'

        self.return_field: str = return_field
        if not self.return_field and self.choices:
            self.return_field = next(iter(self.choices[0]))

        self.hide_return_field = hide_return_field
        self.filter_columns = filter_columns
        self.show_filter = show_filter
        self.sort_column = sort_column
        self.sort_reverse = sort_reverse
        self.min_width = max(len(title) + 6, len(self.subtitle_txt if show_filter else '') + 4)

    def compose(self) -> ComposeResult:
        self.table = DataTable(id="selector-list", cursor_type='row', zebra_stripes=True)
        self.table.border_title = self.title_txt
        self.table.border_subtitle = self.subtitle_txt

        if self.choices:
            # When choices are provided directly
            self.max_columns = max(len(choice) for choice in self.choices) if self.choices else 0
            for column in self.choices[0].keys():
                if self.hide_return_field and column == self.return_field:
                    self.table.add_column(column.replace('_', ' ').title(), key=column, width=0)
                else:
                    self.table.add_column(column.replace('_', ' ').title(), key=column)
            self.load_table(self.choices)
        else:
            # When choices_fn is provided, table is initially empty and loading
            self.table.loading = True

        yield self.table

    def on_mount(self) -> None:
        self.table.focus()
        if self.choices_fn:
            self.load_choices_from_fn()

    @work(exclusive=True)
    async def load_choices_from_fn(self):
        """Load choices by calling the provided function."""
        if not self.choices_fn:
            return

        self.table.loading = True

        result = await self.choices_fn(*self.choices_fn_args)

        # The function might return (title, data) or just data
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], str) and isinstance(result[1], list):
            self.title_txt, self.choices = result
            self.table.border_title = self.title_txt
        elif isinstance(result, list):
            self.choices = result

        if not self.choices:
            self.table.add_column("Result")
            self.table.add_row("No items found.")
            self.table.loading = False
            return

        # Set return_field if not set
        if not self.return_field:
            self.return_field = next(iter(self.choices[0]))

        # Add columns
        for column in self.choices[0].keys():
            if self.hide_return_field and column == self.return_field:
                self.table.add_column(column.replace('_', ' ').title(), key=column, width=0)
            else:
                self.table.add_column(column.replace('_', ' ').title(), key=column)

        self._populate_table(self.choices)
        self.table.loading = False
        self.table.focus()

    @on(DataTable.RowSelected)
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        selected_row = event.row_key.value
        if self.mode == 'choices':
            self.dismiss(str(selected_row))
        else:
            self.dismiss((str(selected_row), self.choices))

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

                filtered_data = filter_data(self.choices, filter)

                # filtered_data = [
                #     row for row in self.choices
                #     if all(
                #         any(val in row[col] if isinstance(row[col], list) else val == row[col] for val in values)
                #         for col, values in filter.items()
                #     )
                # ]

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

    def _populate_table(self, data: list[dict[str, str | list[str]]]):
        """Helper to add rows and sort the table."""
        for choice in data:
            row = [', '.join(cell) if isinstance(cell, list) else cell for cell in choice.values()]
            self.table.add_row(*row, key=str(choice[self.return_field]))

        if self.sort_column:
            def version_key(v: str):
                try:
                    return Version(v)
                except InvalidVersion:
                    return v.lower()
            self.table.sort(self.sort_column, key=lambda r: version_key(r), reverse=self.sort_reverse)

    @work
    async def load_table(self, data: list[dict[str, str | list[str]]]):
        """Loads data into table async."""
        self.table.loading = True
        self._populate_table(data)
        self.table.loading = False
