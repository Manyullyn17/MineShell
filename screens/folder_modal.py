from textual.widgets import Label, Static, Button, Link
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.containers import Grid, Container

class FolderModal(ModalScreen):
    CSS_PATH = 'styles/folder_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
            Binding('up', "focus_move('up')", show=False),
            Binding('down', "focus_move('down')", show=False),
        ]
    
    navigation_map = {
        "ftp-link": {"left":"", "up": "back",       "down": "back", "right": ""},
        "back":     {"left":"", "up": "ftp-link",   "down": "ftp-link",     "right": ""},
    }
    
    def __init__(self, instance_name: str, folder_path: str, ftp_link: str):
        super().__init__()
        self.instance_name = instance_name
        self.folder_path = folder_path
        self.ftp_link = ftp_link

    def compose(self) -> ComposeResult:
        yield Grid(
            Static("Instance: ", classes='folder static'),
            Label(f"{self.instance_name}", id="instance-name", classes='folder label'),
            Static("Folder Path:", classes='folder static'),
            Label(f"{self.folder_path}", id="folder-path", classes='folder label'),
            Link("Open Folder via SFTP", url=self.ftp_link, id="ftp-link", classes='folder link'),
            Container(Button("Back", id="back", classes='folder button'), id='folder-button-container'),
            id='dialog'
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

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