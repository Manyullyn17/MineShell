from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Grid, Center
from textual.events import ScreenResume, ScreenSuspend
from textual.screen import Screen
from textual.widgets import Button, Static, Footer, Header

from screens import InstanceDetailScreen, ManageInstancesScreen
from backend.storage import InstanceRegistry
from helpers import FocusNavigationMixin

class MainMenu(FocusNavigationMixin, Screen):
    CSS_PATH = 'styles/main_screen.tcss'
    BINDINGS = [
        ('crtl+q', 'quit', 'Quit'),
    ] + FocusNavigationMixin.BINDINGS

    # navigation_map = {
    #     "start_stop":       {"left":"", "up": "settings",           "down": "restart",          "right": ""},
    #     "restart":          {"left":"", "up": "start_stop",         "down": "open_instance",    "right": ""},
    #     "open_instance":    {"left":"", "up": "restart",            "down": "manage_instances", "right": ""},
    #     "manage_instances": {"left":"", "up": "open_instance",      "down": "settings",         "right": ""},
    #     "settings":         {"left":"", "up": "manage_instances",   "down": "start_stop",       "right": ""},
    # }

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
                yield Button('Start/Stop', id='start_stop', classes='focusable mainbutton')
                yield Button('Restart', id='restart', classes='focusable mainbutton')
                yield Button('Open Instance', id='open_instance', classes='focusable mainbutton')
                yield Button('Manage Instances', id='manage_instances', classes='focusable mainbutton')
                yield Button('Settings', id='settings', classes='focusable mainbutton')

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

    @on(ScreenResume)
    def on_screen_resume(self, event: ScreenSuspend) -> None:
        if self.status_interval is None:
            self.status_interval = self.set_interval(10, self.update_status)
            self.call_later(self.update_status)

    @on(ScreenSuspend)
    def on_screen_suspend(self, event: ScreenSuspend) -> None:
        if self.status_interval:
            self.status_interval.stop()
            self.status_interval = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'manage_instances':
                self.app.push_screen(ManageInstancesScreen())
            case 'open_instance':
                instance = InstanceRegistry().load().get_default_instance()
                if instance:
                    self.app.push_screen(InstanceDetailScreen(instance=instance))
                else:
                    self.notify('No default instance found.', severity='information', timeout=5)

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
