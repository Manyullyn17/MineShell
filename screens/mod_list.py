from typing import Literal, cast
from datetime import datetime

from textual import work, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Static, Footer, Header, Label, DataTable, Input

from screens.modals import DeleteModal, FilterModal, SortModal
from screens import ModBrowserScreen

from backend.storage import InstanceConfig, ModList
from helpers import CustomInput, CustomTable, sanitize_filename, NavigationMixin, filter_data
from config import DATE_FORMAT, TIME_FORMAT

class ModListScreen(NavigationMixin, Screen):
    CSS_PATH = 'styles/mod_list_screen.tcss'
    BINDINGS = [
        Binding('q', "back", "Back", show=True),
        Binding('escape', "back", "Back", show=False),
        Binding('delete', "delete", "Delete", show=True),
        Binding('e', "enable_disable", "Enable/Disable", show=True),
        Binding('u', "update", "Update", show=True),
        Binding('a', "add_mods", "Add Mods", show=True),
        Binding('f', "filter", "Filter", show=True),
        Binding('s', "sort", "Sort", show=True),
    ] + NavigationMixin.BINDINGS

    # - make delete, enable/disable and update not show up when focusing datatable

    first_load = True

    selected_mod: str | None = None

    current_sorting: Literal['Name', 'Reverse-Name', 'Date', 'Reverse-Date'] = 'Name'

    filtered_data: list[dict] = []

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

            with Horizontal(id='modlist-buttons'):
                yield CustomInput(placeholder='Search Modlist', id='modlist-search', classes='focusable modlist search')
                yield Button('Filter', id='modlist-filter-button', classes='focusable modlist button')
                yield Button('Sort', id='modlist-sort-button', classes='focusable modlist button') # sort by name and install date, normal and reverse
                yield Button('Update', id='modlist-update-button', classes='focusable modlist button')
                yield Button('Add Mods', id='modlist-add-mod-button', classes='focusable modlist button')
                yield Button('Back', id='modlist-back-button', classes='focusable modlist button')

            self.table = CustomTable(id='modlist-table', cursor_type='row', zebra_stripes=True, classes='focusable modlist table')
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
        columns = ['Name', 'Version', 'Type', 'Enabled', 'Source', 'Install Date']

        if self.first_load:
            # Add columns
            for col_name in columns:
                self.table.add_column(col_name, key=col_name.lower().replace(' ', '_'))
            
            # Add hidden datetime column for sorting
            self.table.add_column('datetime', width=0, key='datetime')
            self.first_load = False

        if not data:

            # If registry is empty, just show an empty table
            if not self.modlist.mods:
                self.table.loading = False
                return

            data = self.modlist.to_dict(f'{DATE_FORMAT} {TIME_FORMAT}')

        # Populate rows
        for mod in data:
            try:
                row = [
                    mod.get('name',''),
                    mod.get('version',''),
                    mod.get('type',''),
                    mod.get('enabled',''),
                    mod.get('source',''),
                    mod.get('formatted_date',''),
                    mod.get('install_date',''),
                ]
                self.table.add_row(*row, key=str(mod.get('mod_id','')))
            except KeyError as e:
                self.notify(f"Error adding Mod '{mod.get('name','')}' to Table. {e}", severity='error', timeout=5)

        self.sort_table(self.current_sorting)
        self.table.loading = False

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'modlist-filter-button':
                self.filter_table()
            case 'modlist-sort-button':
                self.open_sort_modal()
            case 'modlist-update-button': # different from action_update, opens modal for selection of update all or update modpack, if not a modpack, only confirmation for update all
                # - implement update all mods
                pass
            case 'modlist-add-mod-button':
                self.action_add_mods()
            case 'modlist-back-button':
                self.app.pop_screen()

    @on(DataTable.RowHighlighted)
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.selected_mod = str(event.row_key.value)

    # - implement opening mod details on select (modal with options to update, enable/disable, delete)
    @on(DataTable.RowSelected)
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if str(event.row_key.value) == '':
            return
        
        pass

    def action_back(self):
        self.app.pop_screen()

    def action_delete(self): # delete mod with confirmation
        def check_delete(delete: bool | None) -> None:
            if delete and self.selected_mod:
                self.delete_mod()
        if not self.selected_mod:
            return
        mod = self.modlist.get_mod(self.selected_mod)
        modname = mod.name if mod else 'Mod'
        self.app.push_screen(DeleteModal(title=f'Delete {modname}?'), check_delete)
    
    def action_enable_disable(self):
        if self.selected_mod:
            self.modlist.toggle_mod(self.selected_mod, self.instance.path)
            self.load_table(self.filtered_data) # reapply filters
            self.sort_table(self.current_sorting) # reapply sorting
            query = self.query_one('#modlist-search', CustomInput).value
            self.search_table(query) # reapply search
    
    # - implement update mod
    def action_update(self): # update currently selected mod
        return
    
    def action_add_mods(self):
        # self.app.push_screen(ModBrowserModal(self.instance.modloader, self.instance.minecraft_version, self.instance.source_api))
        self.app.push_screen(ModBrowserScreen(self.instance))

    def action_filter(self):
        self.filter_table()

    def action_sort(self):
        self.open_sort_modal()

    def delete_mod(self):
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
    
    # - switch to using filter sidebar
    def filter_table(self):
        """Open Filter Modal."""
        def filter_chosen(filter: dict | None) -> None:
            """Filter Table using supplied filter."""
            if filter:
                # - save filters for later use
                formatted_filters = ' | '.join(
                    f"{col.title()}: {', '.join(val) if isinstance(val, list) else val.strip('[]').replace('\'','')}" 
                    for col, val in filter.items()
                )
                self.filter_label.update(f'Filter: {formatted_filters}')
                self.table.clear()

                self.filtered_data = filter_data(self.modlist.to_dict(), filter)

                # - doesn't respect search filtering
                self.load_table(self.filtered_data)
            else:
                self.filter_label.update('')
                self.table.clear()
                self.load_table()
        
        # - pass previous filters to modal if available
        self.app.push_screen(FilterModal(self.modlist.to_dict(), ['type', 'enabled', 'source']), filter_chosen)
        return

    def open_sort_modal(self):
        def check_sort(result: tuple[str, bool] | None) -> None:
            if result:
                column, reverse = result
                self.current_sorting = cast(Literal['Name', 'Reverse-Name', 'Date', 'Reverse-Date'], ('Reverse-' if reverse else '') + column)
                self.sort_table(self.current_sorting)

        self.app.push_screen(SortModal(['Name', 'Date']), check_sort)

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
        column, reverse = sort_map[sort_method]
        self.table.sort(*column, reverse=reverse, key=sort_key)

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed):
        if event.input.id == 'modlist-search':
            query = event.value
            # call table filter function
            self.search_table(query)

    def search_table(self, query: str) -> None:
        """Filter table using supplied query."""
        if not query:
            self.load_table()
            return
        query = sanitize_filename(query)
        data = self.modlist.to_dict(f'{DATE_FORMAT} {TIME_FORMAT}')
        # - doesn't respect filtering
        filtered_data: list[dict] = [
            row for row in data
            if sanitize_filename(str(row.get("name", ""))).startswith(query)
        ]
        if not filtered_data:
            filtered_data = [{"name": "No results found"}]
        self.load_table(filtered_data)

