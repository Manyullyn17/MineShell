from textual.app import ComposeResult
from textual.widgets import Button, Static, Footer, Header, Label, DataTable
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from backend.storage.instance import InstanceConfig, ModList
from helpers import SmartInput

class ModListScreen(Screen):
    CSS_PATH = 'styles/mod_list_screen.tcss'
    BINDINGS = [
        Binding('q', "back", "Back", show=True),
        Binding('up', "focus_move('up')", show=False),
        Binding('down', "focus_move('down')", show=False),
        Binding('left', "focus_move('left')", show=False),
        Binding('right', "focus_move('right')", show=False),
    ]

    navigation_map = {
        "start_stop":       {"left":"", "up": "settings",           "down": "restart",          "right": ""},
        "restart":          {"left":"", "up": "start_stop",         "down": "open_instance",    "right": ""},
        "open_instance":    {"left":"", "up": "restart",            "down": "manage_instances", "right": ""},
        "manage_instances": {"left":"", "up": "open_instance",      "down": "settings",         "right": ""},
        "settings":         {"left":"", "up": "manage_instances",   "down": "start_stop",       "right": ""},
    }

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
                if self.instance.modpack_version:
                    yield Static(f'Version: {self.instance.modpack_version}', classes='modlist info')
                yield Static(f'Modloader: {self.instance.formatted_modloader()}', classes='modlist info') 
                if not self.instance.modpack_id:
                    yield Static(f'Modloader Version: {self.instance.modloader_version}', classes='modlist info')
                self.mod_count = Label(f'Mods: {len(self.modlist.mods)}', id='modlist-mod-count', classes='modlist info')
                yield self.mod_count
                # how does reactivity work? can i just update the number and it updates somehow?

            with Horizontal(id='modlist-buttons'):
                yield SmartInput(placeholder='Search Modlist', classes='modlist search')
                yield Button('Filter', id='modlist-filter-button', classes='modlist button')
                yield Button('Update', id='modlist-update-button', classes='modlist button')
                yield Button('Add Mods', id='modlist-add-mod-button', classes='modlist button')

            self.table = DataTable(classes='modlist table')
            yield self.table

        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.instance.name + ' - Modlist'

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'gg':
                return

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
