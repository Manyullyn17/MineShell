from textual.app import ComposeResult
from textual.widgets import Button, Static, Footer, Header
from textual.screen import Screen
from textual.containers import Grid, Center
from textual.binding import Binding
from backend.storage.instance import InstanceConfig, ModList

class ModListScreen(Screen):
    CSS_PATH = 'styles/main_screen.tcss'
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

        with Grid():
            yield Static()

        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.instance.name

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
