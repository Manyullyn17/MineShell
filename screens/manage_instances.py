from shutil import rmtree
from pathlib import Path

from textual import work, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.events import MouseDown, ScreenResume, Key
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header

from screens import InstanceDetailScreen, NewInstanceScreen
from screens.modals import DeleteModal, OptionModal

from backend.storage import InstanceRegistry
from helpers import CustomTable, FocusNavigationMixin

class ManageInstancesScreen(FocusNavigationMixin, Screen):
    CSS_PATH = 'styles/manage_instances_screen.tcss'
    BINDINGS = [
        ('q', 'back', 'Back'),
        Binding('escape', 'back', show=False),
        ('n', 'new_instance', 'New Instance'),
        ('d', 'default_instance', 'Set Default Instance'),
        ('del', 'delete', 'Delete'),
    ] + FocusNavigationMixin.BINDINGS

    navigation_map = {
            "instances_list":   {"left":"",                 "up": "",               "down": "new_instance", "right": "new_instance"},
            "new_instance":     {"left":"instances_list",   "up": "instances_list", "down": "",             "right": "back"},
            "back":             {"left":"new_instance",     "up": "instances_list", "down": "",             "right": ""},
    }

    selected_instance: str | None = None # instance_id

    registry: InstanceRegistry

    mouse_button: int = 0

    mouse_x: int = 0

    mouse_y: int = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        self.table = CustomTable(id='instances_list', cursor_type='row', zebra_stripes=True)
        yield self.table

        with Horizontal(id='button-row'):
            yield Button('New Instance', id='new_instance', classes='instancebutton')
            yield Button('Back', id='back', classes='instancebutton')

        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = 'Manage Instances'
        self.registry = InstanceRegistry.load()

    @on(ScreenResume)
    def on_screen_resume(self, event: ScreenResume) -> None:
        self.registry = InstanceRegistry.load() # reload registry
        self.load_table()
        self.mouse_button = 0

    @work
    async def load_table(self):
        self.table.loading = True
        self.table.clear()
        self.table.columns.clear()
        columns = ['Name', 'Status', 'Created', 'Pack Version', 'Modloader', 'Minecraft Version', 'Default']

        # Add columns
        for col_name in columns:
            self.table.add_column(col_name)
        
        # Add hidden datetime column for sorting
        self.table.add_column('datetime', width=0)

        # If registry is empty, just show an empty table
        if not self.registry.instances:
            self.table.loading = False

        # - sort default instance first?
        # Populate rows
        for instance in self.registry.instances:
            row = [
                instance.name or '',
                instance.status.capitalize() if instance.status else '',
                instance.formatted_date(),
                instance.pack_version or '',
                instance.formatted_modloader(),
                instance.minecraft_version or '',
                # - show nothing if not default?
                'True' if instance.instance_id == self.registry.default_instance else False,
                instance.created or '',
            ]
            self.table.add_row(*row, key=instance.instance_id)
        try:
            row_index = self.table.get_row_index(self.selected_instance) if self.selected_instance else None
        except:
            row_index = 0
        if row_index: # doesn't run if row_index is 0 or None but it auto selects first row anyway
            self.table.move_cursor(row=row_index)

        self.table.loading = False
        self.table.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'back':
                self.app.pop_screen()
            case 'new_instance':
                def instance_created(instance_id: str | None) -> None:
                    if not instance_id:
                        return
                    # reload registry
                    self.registry = InstanceRegistry.load()
                    self.selected_instance = instance_id
                    # open Instance Detail Screen for new Instance
                    self.open_instance(instance_id)
                self.app.push_screen(NewInstanceScreen(), instance_created)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.selected_instance = str(event.row_key.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        match self.mouse_button:
            case 1: # left click
                selected_instance = str(event.row_key.value)
                self.open_instance(selected_instance)
                self.mouse_button = 0 # reset mouse_button
            case 3: # right click
                self.open_context_menu()

    @on(MouseDown)
    def on_mouse_down(self, event: MouseDown):
        self.mouse_button = event.button
        self.mouse_x = event.x
        self.mouse_y = event.y

    @on(Key)
    def on_key(self, event: Key):
        if event.key == 'enter' and self.focused and self.focused.id == 'instances_list':
            self.mouse_button = 1 # pretend left click happened, otherwise enter doesn't work

    def action_back(self):
        self.app.pop_screen()

    def action_new_instance(self):
        def check_delete(delete: bool | None) -> None:
            if delete:
                self.delete_instance()

        self.app.push_screen(NewInstanceScreen(), check_delete)

    def action_default_instance(self):
        if self.selected_instance:
            self.registry.set_default_instance(self.selected_instance)

    def action_delete(self):
        def check_delete(delete: bool | None) -> None:
            if delete and self.selected_instance:
                self.delete_instance()
        if not self.selected_instance:
            return
        self.app.push_screen(DeleteModal(), check_delete)

    def delete_instance(self):
        self.registry = InstanceRegistry.load()
        if self.selected_instance:
            instance = self.registry.get_instance(self.selected_instance)
            if not instance:
                self.notify('Could not find instance.', severity='error', timeout=5)
                self.load_table()
                return
            
            self.registry.remove_instance(self.selected_instance)
            if instance.path.exists():
                try:
                    rmtree(Path('instances') / self.selected_instance)
                except:
                    self.notify('Could not delete instance files.', severity='error', timeout=5)
                    return
            else:
                self.notify('Could not find instance files.', severity='error', timeout=5)
            self.registry.save()
            self.load_table()

    def open_instance(self, instance_id: str):
        instance = self.registry.get_instance(instance_id)
        if instance:
            self.app.push_screen(InstanceDetailScreen(instance))

    def open_context_menu(self):
        def context_handler(result: str | None) -> None:
            if not result:
                return
            match result:
                case 'set_default':
                    self.action_default_instance()
                case 'edit':
                    pass
                case 'delete':
                    self.action_delete()
                case default:
                    pass
                # - add more buttons
        self.mouse_button = 0 # reset mouse_button to prevent loops
        disable_set_default = False
        if self.registry.default_instance == self.selected_instance:
            disable_set_default = True
        self.app.push_screen(OptionModal([('set_default', disable_set_default), 'edit', 'delete'], pos=(self.mouse_x, self.mouse_y)), context_handler)
        # - what does 'edit' do? i forgot, does it just open the instance?
