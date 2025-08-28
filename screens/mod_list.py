from typing import Literal, cast
from datetime import datetime
from textual import work
from textual.app import ComposeResult
from textual.widgets import Button, Static, Footer, Header, Label, DataTable
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from screens.delete_modal import DeleteModal
from screens.filter_modal import FilterModal
from screens.sort_modal import SortModal
from backend.storage.instance import InstanceConfig, ModList
from helpers import SmartInput, CustomTable
from config import DATE_FORMAT, TIME_FORMAT

class ModListScreen(Screen):
    CSS_PATH = 'styles/mod_list_screen.tcss'
    BINDINGS = [
        Binding('q', "back", "Back", show=True),
        Binding('d', "delete", "Delete", show=True),
        Binding('e', "enable_disable", "Enable/Disable", show=True),
        Binding('u', "update", "Update", show=True),
        Binding('a', "add_mods", "Add Mods", show=True),
        Binding('up', "focus_move('up')", show=False),
        Binding('down', "focus_move('down')", show=False),
        Binding('left', "focus_move('left')", show=False),
        Binding('right', "focus_move('right')", show=False),
    ]

    navigation_map = {
        "modlist-search":           {"left": "",                         "up": "",  "down": "modlist-table", "right": "modlist-filter-button"},
        "modlist-filter-button":    {"left": "modlist-search",           "up": "",  "down": "modlist-table", "right": "modlist-sort-button"},
        "modlist-sort-button":      {"left": "modlist-filter-button",    "up": "",  "down": "modlist-table", "right": "modlist-update-button"},
        "modlist-update-button":    {"left": "modlist-sort-button",      "up": "",  "down": "modlist-table", "right": "modlist-add-mod-button"},
        "modlist-add-mod-button":   {"left": "modlist-update-button",    "up": "",  "down": "modlist-table", "right": ""},
        "modlist-table":            {"left": "",                         "up": "modlist-search", "down": "", "right": ""}
    }

    first = True

    selected_mod: str | None = None

    current_sorting: Literal['Name', 'Reverse-Name', 'Date', 'Reverse-Date'] = 'Name'

    def __init__(self, instance: InstanceConfig) -> None:
        super().__init__()
        self.instance: InstanceConfig = instance
        self.modlist: ModList = instance.mods

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical():
            with Horizontal(id='modlist-info'):
                if self.instance.modpack_name:
                    yield Static(f'Modpack: {self.instance.modpack_name}', classes='modlist info')
                    yield Static(classes='modlist info spacer')
                if self.instance.modpack_version:
                    yield Static(f'Version: {self.instance.modpack_version}', classes='modlist info')
                    yield Static(classes='modlist info spacer')
                yield Static(f'Modloader: {self.instance.formatted_modloader()}', classes='modlist info') 
                yield Static(classes='modlist info spacer')
                if not self.instance.modpack_id:
                    yield Static(f'Modloader Version: {self.instance.modloader_version}', classes='modlist info')
                    yield Static(classes='modlist info spacer')
                self.mod_count = Label(f'Mods: {len(self.modlist.mods)}', id='modlist-mod-count', classes='modlist info')
                yield self.mod_count
                # how does reactivity work? can i just update the number and it updates somehow?

            with Horizontal(id='modlist-buttons'):
                yield SmartInput(placeholder='Search Modlist', id='modlist-search', classes='modlist search')
                yield Button('Filter', id='modlist-filter-button', classes='modlist button')
                yield Button('Sort', id='modlist-sort-button', classes='modlist button') # sort by name and install date, normal and reverse
                yield Button('Update', id='modlist-update-button', classes='modlist button')
                yield Button('Add Mods', id='modlist-add-mod-button', classes='modlist button')

            self.table = CustomTable(classes='modlist table', id='modlist-table', cursor_type='row', zebra_stripes=True)
            yield self.table
            self.filter_label = Label(id='modlist-filter-label')
            yield self.filter_label

        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.instance.name + ' - Modlist'
        self.table.focus()
        self.load_table()

    @work
    async def load_table(self, data: list[dict[str, str | list[str]]] | None = None):
        self.table.loading = True
        self.mod_count.update(f'Mods: {len(self.modlist.mods)}')
        self.table.clear()
        # self.table.columns.clear()
        columns = ['Name', 'Version', 'Type', 'Enabled', 'Source', 'Install Date']

        if self.first:
            # Add columns
            for col_name in columns:
                self.table.add_column(col_name, key=col_name.lower().replace(' ', '_'))
            
            # Add hidden datetime column for sorting
            self.table.add_column('datetime', width=0, key='datetime')
            self.first = False

        if not data:

            # If registry is empty, just show an empty table
            if not self.modlist.mods:
                self.table.loading = False
                return

            data = self.modlist.to_dict(f'{DATE_FORMAT} {TIME_FORMAT}')

        # Populate rows
        for mod in data:
            row = [
                mod['name'],
                mod['version'],
                mod['type'],
                mod['enabled'],
                mod['source'],
                mod['formatted_date'],
                mod['install_date'],
            ]
            self.table.add_row(*row, key=str(mod['mod_id']))

        self.sort_table(self.current_sorting)
        self.table.loading = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'modlist-filter-button':
                self.filter_table()
            case 'modlist-sort-button':
                def check_sort(result: tuple[str, bool] | None) -> None:
                    if result:
                        column, reverse = result
                        self.current_sorting = cast(Literal['Name', 'Reverse-Name', 'Date', 'Reverse-Date'], ('Reverse-' if reverse else '') + column)
                        self.sort_table(self.current_sorting)

                self.app.push_screen(SortModal(['Name', 'Date']), check_sort)
                return
            case 'modlist-update-button': # different from action_update, opens modal for selection of update all or update modpack, if not a modpack, only confirmation for update all
                return
            case 'modlist-add-mod-button':
                self.action_add_mods()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.selected_mod = str(event.row_key.value)

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
        self.app.pop_screen()

    def action_delete(self): # delete mod with confirmation
        def check_delete(delete: bool | None) -> None:
            if delete and self.selected_mod:
                self.delete_instance()
        if not self.selected_mod:
            return
        mod = self.modlist.get_mod(self.selected_mod)
        modname = mod.name if mod else 'Mod'
        self.app.push_screen(DeleteModal(title=f'Delete {modname}?'), check_delete)
    
    def action_enable_disable(self):
        return
    
    def action_update(self): # update currently selected mod
        return
    
    def action_add_mods(self):
        return

    def delete_instance(self):
        if self.selected_mod:
            mod = self.modlist.get_mod(self.selected_mod)
            if not self.modlist.remove_mod(self.selected_mod, self.instance.path):
                if mod:
                    self.notify(f"Could not remove {mod.type.capitalize()} '{mod.name}.'", severity='error', timeout=5)
                else:
                    self.notify(f"Could not remove Mod.", severity='error', timeout=5)
                return
            
            self.modlist.save(self.instance.path / "mods")
            self.load_table()
    
    def filter_table(self):
        def filter_chosen(filter: dict | None) -> None:
            if filter:
                formatted_filters = ' | '.join(
                    f"{col.title()}: {', '.join(val) if isinstance(val, list) else val.strip('[]').replace('\'','')}" 
                    for col, val in filter.items()
                )
                self.filter_label.update(f'Filter: {formatted_filters}')
                self.table.clear()

                filtered_data = [
                    row for row in self.modlist.to_dict()
                    if all(
                        any(val in row[col] if isinstance(row[col], list) else val == row[col] for val in values)
                        for col, values in filter.items()
                    )
                ]

                self.load_table(filtered_data)
            else:
                self.filter_label.update('')
                self.table.clear()
                self.load_table()
        
        self.app.push_screen(FilterModal(self.modlist.to_dict(), ['type', 'enabled', 'source']), filter_chosen)
        return

    def sort_table(self, sort_method: Literal['Name', 'Reverse-Name', 'Date', 'Reverse-Date'] = 'Name'):
        sort_map = {
            # key           column                  reverse
            "Name":         (["name"],              False),
            "Reverse-Name": (["name"],              True),
            "Date":         (["datetime", "name"],  False),
            "Reverse-Date": (["datetime", "name"],  True),
        }
        def sort_key(value):
            if isinstance(value, tuple):
                dt_str, name = value
                dt_sort = -datetime.fromisoformat(dt_str).replace(microsecond=0).timestamp()
                return (dt_sort, name.lower())
            else:
                return str(value).lower()
        if sort_method:
            column, reverse = sort_map[sort_method]
            self.table.sort(*column, reverse=reverse, key=sort_key)
