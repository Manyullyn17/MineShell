from textual.app import ComposeResult
from textual.widgets import Button, Footer, Header, Static
from textual.screen import Screen
from textual.containers import Grid
from textual.binding import Binding
from screens.folder_modal import FolderModal

class InstanceDetailScreen(Screen):
    CSS_PATH = 'styles/instance_detail_screen.tcss'
    BINDINGS = [
        ('q', 'back', 'Back'),
        Binding('escape', 'back', show=False),
        ('s', 'start_stop', 'Start/Stop'),
        ('r', 'restart', 'Restart'),
        Binding('up', "focus_move('up')", show=False),
        Binding('down', "focus_move('down')", show=False),
        Binding('left', "focus_move('left')", show=False),
        Binding('right', "focus_move('right')", show=False),
    ]

    navigation_map = {
        "start_stop":   {"left":"settings",     "up": "configs",    "down": "configs",      "right": "restart"},
        "restart":      {"left":"start_stop",   "up": "backups",    "down": "backups",      "right": "console"},
        "console":      {"left":"restart",      "up": "folder",     "down": "folder",       "right": "modlist"},
        "modlist":      {"left":"console",      "up": "delete",     "down": "delete",       "right": "settings"},
        "settings":     {"left":"modlist",      "up": "back",       "down": "back",         "right": "start_stop"},
        "configs":      {"left":"back",         "up": "start_stop", "down": "start_stop",   "right": "backups"},
        "backups":      {"left":"configs",      "up": "restart",    "down": "restart",      "right": "folder"},
        "folder":       {"left":"backups",      "up": "console",    "down": "console",      "right": "delete"},
        "delete":       {"left":"folder",       "up": "modlist",    "down": "modlist",      "right": "back"},
        "back":         {"left":"delete",       "up": "settings",   "down": "settings",     "right": "configs"},
    }

    def __init__(self, instance_name: str) -> None:
        super().__init__()
        self.instance_name = instance_name

    def compose(self) -> ComposeResult:
        self.running = ''
        self.uptime = ''
        self.cpu = ''
        self.tps = ''
        self.players = ''
        self.ram = ''
        self.mc_version = '1.20.1'
        self.modloader = 'Fabric 0.15.0'

        yield Header(show_clock=True)

        with Grid(id='instance-grid'):
            self.status_running = Static(id='status-running', classes='detail status left')
            yield self.status_running
            self.status_uptime = Static(id='status-uptime', classes='detail status middle')
            yield self.status_uptime
            self.status_cpu = Static(id='status-cpu', classes='detail status right')
            yield self.status_cpu
            self.status_tps = Static(id='status-tps', classes='detail status left ')
            yield self.status_tps
            self.status_players = Static(id='status-players', classes='detail status middle')
            yield self.status_players
            self.status_ram = Static(id='status-ram', classes='detail status right')
            yield self.status_ram
            # get mc version and modloader once on start up
            self.status_mc_version = Static(f'Minecraft: {self.mc_version} ({self.modloader})', id='status-mc-version', classes='detail status left')
            yield self.status_mc_version

        yield Static(id='grid-spacer')

        with Grid(id='button-grid'):
            yield Button('Start/Stop', id='start_stop', classes='detail button')
            yield Button('Restart', id='restart', classes='detail button')
            yield Button('Console', id='console', classes='detail button')
            yield Button('Mod List', id='modlist', classes='detail button')
            yield Button('Settings', id='settings', classes='detail button')
            yield Button('Configs', id='configs', classes='detail button')
            yield Button('Backups', id='backups', classes='detail button')
            yield Button('Open Folder', id='folder', classes='detail button')
            yield Button('Delete Instance', id='delete', classes='detail button')
            yield Button('Back', id='back', classes='detail button')

        yield Footer()

    def on_mount(self) -> None:
        self.title = 'Mineshell'
        self.sub_title = self.instance_name
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
            case 'start_stop':
                print('start/stop') # send start/stop command depending on status
            case 'restart':
                print('restart') # send stop command, then start command
            case 'console':
                print('console') # open console screen
            case 'modlist':
                print('modlist') # open modlist screen
            case 'settings':
                print('settings') # open settings screen
            case 'configs':
                print('configs') # open configs screen
            case 'backups':
                print('backups') # open backups screen
            case 'folder':
                self.app.push_screen(FolderModal('test instance', 'home/manyullyn/mineshell/\ninstances/test_instance', 'sftp://manyullyn@192.168.0.200/home/manyullyn/mineshell/instances/test_instance/')) # placeholder values
            case 'delete':
                print('delete') # delete instance
            case 'back':
                self.app.pop_screen()
            
    def action_back(self):
        self.app.pop_screen()

    def action_start_stop(self): # implement
        print('start/stop')

    def action_restart(self): # implement
        print('restart')

    def action_focus_move(self, direction: str):
        focused = self.focused
        if not focused or not focused.id:
            return
        next_id = self.navigation_map.get(focused.id, {}).get(direction)
        if next_id:
            next_widget = self.query_one(f'#{next_id}')
            next_widget.focus()

    async def update_status(self):
        # actually get status dynamically
        self.running = 'Running'
        self.uptime = '00:02:34'
        self.cpu = '15%'
        self.tps = '19.9'
        self.players = '3/20'
        self.ram = '1.2/8GB'
        
        self.status_running.update(f'Status: {self.running}')
        self.status_uptime.update(f'Uptime: {self.uptime}')
        self.status_cpu.update(f'CPU: {self.cpu}')
        self.status_tps.update(f'TPS: {self.tps}')
        self.status_players.update(f'Players: {self.players}')
        self.status_ram.update(f'RAM: {self.ram}')

