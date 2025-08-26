from shutil import rmtree
from pathlib import Path
from textual import work
from textual.app import ComposeResult
from textual.widgets import Button, DataTable, Footer, Header
from textual.screen import Screen
from textual.containers import Horizontal
from screens.instance_detail import InstanceDetailScreen
from screens.new_instance import NewInstanceScreen
from screens.delete_modal import DeleteModal
from textual.binding import Binding
from backend.storage.instance import InstanceRegistry

class ManageInstancesScreen(Screen):
    CSS_PATH = 'styles/manage_instances_screen.tcss'
    BINDINGS = [
        ('q', 'back', 'Back'),
        Binding('escape', 'back', show=False),
        ('n', 'new_instance', 'New Instance'),
        ('d', 'delete', 'Delete'),
        Binding('up', "focus_move('up')", show=False),
        Binding('down', "focus_move('down')", show=False),
        Binding('left', "focus_move('left')", show=False),
        Binding('right', "focus_move('right')", show=False),
    ]

    navigation_map = {
            "instances_list":   {"left":"back",             "up": "",               "down": "",                 "right": "new_instance"},
            "new_instance":     {"left":"instances_list",   "up": "instances_list", "down": "instances_list",   "right": "back"},
            "back":             {"left":"new_instance",     "up": "instances_list", "down": "instances_list",   "right": "instances_list"},
    }

    selected_instance: str | None = None # instance_id

    registry: InstanceRegistry

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        self.table = DataTable(id='instances_list', cursor_type='row', zebra_stripes=True)
        yield self.table

        with Horizontal(id='button-row'):
            yield Button('New Instance', id='new_instance', classes='instancebutton')
            yield Button('Back', id='back', classes='instancebutton')

        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = 'Manage Instances'
        self.table.loading = True
        self.registry = InstanceRegistry.load()

    def _on_screen_resume(self) -> None:
        self.load_table()

    @work
    async def load_table(self):
        self.table.clear()
        self.table.columns.clear()
        columns = ['Name', 'Status', 'Created', 'Pack Version', 'Modloader', 'Minecraft Version']

        # Add columns
        for col_name in columns:
            self.table.add_column(col_name)
        
        # Add hidden datetime column for sorting
        self.table.add_column('datetime', width=0)

        self.registry = InstanceRegistry.load() # reload registry

        # If registry is empty, just show an empty table
        if not self.registry.instances:
            self.table.loading = False

        # Populate rows
        for instance in self.registry.instances:
            row = [
                instance.name or '',
                instance.status.capitalize() if instance.status else '',
                instance.formatted_date(),
                instance.pack_version or '',
                instance.formatted_modloader(),
                instance.minecraft_version or '',
                instance.created or ''
            ]
            self.table.add_row(*row, key=instance.instance_id)

        self.table.loading = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'back':
                self.app.pop_screen()
            case 'new_instance':
                self.app.push_screen(NewInstanceScreen())

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.selected_instance = str(event.row_key.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        selected_instance = str(event.row_key.value)
        instance = self.registry.get_instance(selected_instance)
        if instance:
            self.app.push_screen(InstanceDetailScreen(instance))

    def action_back(self):
        self.app.pop_screen()

    def action_new_instance(self):
        def check_delete(delete: bool | None) -> None:
            if delete:
                self.delete_instance()

        self.app.push_screen(NewInstanceScreen(), check_delete)

    def action_delete(self):
        def check_delete(delete: bool | None) -> None:
            if delete and self.selected_instance:
                self.delete_instance()
        if not self.selected_instance:
            return
        self.app.push_screen(DeleteModal(), check_delete)

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

    def delete_instance(self):
        self.registry = InstanceRegistry.load()
        if self.selected_instance:
            self.registry.remove_instance(self.selected_instance)
            try:
                rmtree(Path('instances') / self.selected_instance)
            except:
                self.notify('Could not delete instance files.', severity='error', timeout=5)
                return
            self.registry.save()
            self.load_table()
