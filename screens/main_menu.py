from textual.app import ComposeResult
from textual.widgets import Button, Static, Footer, Header
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, Grid, Center
from screens.instance_detail import InstanceDetailScreen
from screens.manage_instances import ManageInstancesScreen
from textual.binding import Binding

class MainMenu(Screen):
    CSS_PATH = 'styles/main_screen.tcss'
    BINDINGS = [
        ('crtl+q', 'quit', 'Quit'),
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

    def compose(self) -> ComposeResult:
        self.instance_name = ''
        self.instance_status = ''
        self.players = ''
        self.uptime = ''
        self.cpu = ''
        self.ram = ''

        yield Header(show_clock=True)

        with Horizontal():
            with Vertical(id='buttons'):
                yield Button('Start/Stop', id='start_stop', classes='mainbutton')
                yield Button('Restart', id='restart', classes='mainbutton')
                yield Button('Open Instance', id='open_instance', classes='mainbutton')
                yield Button('Manage Instances', id='manage_instances', classes='mainbutton')
                yield Button('Settings', id='settings', classes='mainbutton')

            with Vertical():
                self.instance_info = Static(id='instance-info')
                yield self.instance_info

                self.status_players = Static(id='status-players', classes='status')
                self.status_uptime = Static(id='status-uptime', classes='status')
                self.status_cpu = Static(id='status-cpu', classes='status')
                self.status_ram = Static(id='status-ram', classes='status')

                yield Center(
                    Grid(
                        self.status_players,
                        self.status_uptime,
                        self.status_cpu,
                        self.status_ram,
                        id='status-grid'
                    )
                )

        yield Footer()

    def on_mount(self) -> None:
        # - get name and status dynamically
        self.update_instance_info('Server', True)
        self.status_interval = self.set_interval(10, self.update_status)
        self.call_later(self.update_status)

    def _on_screen_resume(self) -> None:
        if self.status_interval is None:
            self.status_interval = self.set_interval(10, self.update_status)
            self.call_later(self.update_status)
        return super()._on_screen_resume()
    
    def _on_screen_suspend(self) -> None:
        if self.status_interval:
            self.status_interval.stop()
            self.status_interval = None
        return super()._on_screen_suspend()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'manage_instances':
                self.app.push_screen(ManageInstancesScreen())
            case 'open_instance':
                return
                # placeholder until setting and getting default instance is implemented
                # self.app.push_screen(InstanceDetailScreen(instance_name='Placeholder'))

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

    def update_instance_info(self, instance_name: str, running: bool, stopping: bool=False):
        self.instance_name = instance_name
        if running:
            self.instance_status = '🟢 Running'
        elif stopping:
            self.instance_status = '🟠 Stopping'
        else:
            self.instance_status = '🔴 Stopped'
        self.instance_info.update(f'Default Instance: {self.instance_name} ({self.instance_status})')

    async def update_status(self):
        # - add method of getting info
        self.players = '2/4'
        self.uptime = '00:21:17'
        self.cpu = '15%'
        self.ram = '8.2/12GB'
        self.status_players.update(f'Players online: {self.players}')
        self.status_uptime.update(f'Server uptime: {self.uptime}')
        self.status_cpu.update(f'CPU: {self.cpu}')
        self.status_ram.update(f'RAM: {self.ram}')

