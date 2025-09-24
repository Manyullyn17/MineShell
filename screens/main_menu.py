from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Grid, Center
from textual.events import ScreenResume, ScreenSuspend
from textual.screen import Screen
from textual.widgets import Button, Static, Footer, Header

from screens import InstanceDetailScreen, ManageInstancesScreen
from backend.storage import InstanceRegistry
from helpers import NavigationMixin

class MainMenu(NavigationMixin, Screen):
    CSS_PATH = 'styles/main_screen.tcss'
    BINDINGS = [
        ('crtl+q', 'quit', 'Quit'),
    ] + NavigationMixin.BINDINGS

    registry: InstanceRegistry

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal():
            with Vertical(id='buttons'):
                yield Button('Start/Stop', id='start_stop', classes='focusable mainbutton')
                yield Button('Restart', id='restart', classes='focusable mainbutton')
                yield Button('Open Instance', id='open_instance', classes='focusable mainbutton')
                yield Button('Manage Instances', id='manage_instances', classes='focusable mainbutton')
                yield Button('Settings', id='settings', classes='focusable mainbutton')

            with Vertical(id='info'):
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
        self.registry = InstanceRegistry.load()
        self.default_instance = self.registry.get_default_instance()
        self.update_default_instance()
        self.status_interval = self.set_interval(10, self.update_status)
        self.call_later(self.update_status)

    @on(ScreenResume)
    def on_screen_resume(self, event: ScreenSuspend) -> None:
        if self.default_instance:
            # reload registry and default instance
            self.registry = InstanceRegistry.load()
        self.update_default_instance()
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
                if self.default_instance:
                    self.app.push_screen(InstanceDetailScreen(instance=self.default_instance))
                else:
                    self.notify('No default instance found.', severity='information', timeout=5)

    def update_default_instance(self):
        self.default_instance = self.registry.get_default_instance()
        self.update_instance_info()

    def update_instance_info(self):
        if self.default_instance:
            if self.default_instance.running:
                instance_status = '🟢 Running'
            elif self.default_instance.stopping:
                instance_status = '🟠 Stopping'
            else:
                instance_status = '🔴 Stopped'
            self.instance_info.update(f'Default Instance: {self.default_instance.name} ({instance_status})')
        else:
            self.instance_info.update('Default Instance: No Default Instance')

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
