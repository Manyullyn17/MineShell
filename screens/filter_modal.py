from textual import on
from textual.widgets import Label, Button, Select
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.containers import Grid
from helpers import CustomSelect

class FilterModal(ModalScreen[dict]):
    """A reusable modal that can show a list of values with optional extra info."""
    CSS_PATH = 'styles/filter_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
            Binding('up', "focus_move('up')", show=False),
            Binding('down', "focus_move('down')", show=False),
            Binding('left', "focus_move('left')", show=False),
            Binding('right', "focus_move('right')", show=False),
            Binding('r', "reset", show=False),
        ]

    def __init__(self, choices: list[dict[str, str | list[str]]], filter_columns: list[str] | None = None):
        super().__init__()
        # Normalize choices: make sure every item is a list
        self.choices = choices
        self.column_names = list(choices[0])
        self.filter_columns = filter_columns if filter_columns else self.column_names
        self.filters: dict[str, str] = {}
        self.navigation_map: dict[str, dict] = {}
        self.select_ids = []

    def compose(self) -> ComposeResult:
        self.grid = Grid(id='filter-grid')

        rows = len(self.filter_columns) + 1
        self.grid.styles.grid_size_rows = rows
        self.grid.styles.grid_size_columns = 2
        longest = len(max(self.column_names, key=len))
        self.grid.styles.grid_columns = f'{longest+2} 1fr'
        row_size = " 3"*(len(self.filter_columns))
        self.grid.styles.grid_rows = f'{row_size} 4'
        self.grid.styles.height = str(rows*3 + 3)

        self.grid.border_title = 'Filter Table'
        self.grid.border_subtitle = 'r to reset'
        yield self.grid
        
    def on_mount(self):
        unique_values = {
            key: list({
                elem
                for row in self.choices
                for cell in (row[key] if isinstance(row[key], list) else [row[key]])
                for elem in ([cell] if isinstance(cell, str) else cell)  # flatten one level
            })
            for key in self.filter_columns
        }

        # for row in self.choices:
        #     for col, value in zip(self.columns, row):
        #         if isinstance(value, list):
        #             for item in value:
        #                 unique_values[col].add(item)
        #             continue
        #         unique_values[col].add(value)

        # unique_values = {col: list(values) for col, values in unique_values.items()}

        def sort_key(v: str):
            if v.replace(".", "").isdigit():  # crude check for version numbers
                # Split by dots and convert to ints for proper version comparison
                return (0, tuple(map(int, v.split("."))))
            else:
                return (1, v.lower())  # alphabetical for text

        for column in self.filter_columns:
            first = unique_values[column][0].rsplit('.')[0]
            reverse = True if first.isdigit() else False
            self.grid.mount(Label(column.replace('_', ' ').title(), classes='filter label'))
            self.grid.mount(CustomSelect.from_values(sorted(unique_values[column], key=sort_key, reverse=reverse), id=f'filter-{column}', classes='filter select'))
            self.select_ids.append(f'filter-{column}')

        for i, select_id in enumerate(self.select_ids):
            nav = {"left": "", "right": ""}

            # Up
            if i == 0:
                nav["up"] = ""
            else:
                nav["up"] = self.select_ids[i - 1]

            # Down
            if i == len(self.select_ids) - 1:
                nav["down"] = 'filter-done-button'
            else:
                nav["down"] = self.select_ids[i + 1]

            self.navigation_map[select_id] = nav
        
        self.navigation_map['filter-done-button'] = {'left': 'filter-back-button', 'up': self.select_ids[-1], 'down': '', 'right': ''}
        self.navigation_map['filter-back-button'] = {'left': '', 'up': self.select_ids[-1], 'down': '', 'right': 'filter-done-button'}

        self.grid.mount(Button('Back', id='filter-back-button', classes='filter button'))
        self.grid.mount(Button('Done', id='filter-done-button', classes='filter button'))
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'filter-back-button':
                self.action_back()
            case 'filter-done-button':
                self.action_done()

    @on(Select.Changed)
    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value and event.select.id:
            if event.value != Select.BLANK:
                self.filters[event.select.id.rsplit('-', 2)[-1]] = str(event.value)
            else:
                del self.filters[event.select.id.rsplit('-', 2)[-1]]
    
    def action_focus_move(self, direction: str):
        focused = self.focused
        if not focused or not focused.id:
            return
        next_id = self.navigation_map.get(focused.id, {}).get(direction)
        if next_id:
            next_widget = self.query_one(f'#{next_id}')
            next_widget.focus()

    def action_back(self):
        self.dismiss()

    def action_done(self):
        self.dismiss(self.filters)

    def action_reset(self):
        for id in self.select_ids:
            self.query_one(f'#{id}', expect_type=Select).value = Select.BLANK
        self.filters = {}
