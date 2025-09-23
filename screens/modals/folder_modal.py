from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Container
from textual.widgets import Label, Static, Button, Link

from helpers import CustomModal, NavigationMixin

class FolderModal(NavigationMixin, CustomModal):
    CSS_PATH = 'styles/folder_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
        ] + NavigationMixin.BINDINGS

    def __init__(self, instance_name: str, folder_path: str, ftp_link: str):
        super().__init__()
        self.instance_name = instance_name
        self.folder_path = folder_path
        self.ftp_link = ftp_link

    def compose(self) -> ComposeResult:
        self.grid = Grid(id='dialog')
        with self.grid:
            yield Static("Instance: ", classes='folder static')
            yield Label(f"{self.instance_name}", id="instance-name", classes='folder label')
            yield Static("Folder Path:", classes='folder static')
            yield Label(f"{self.folder_path}", id="folder-path", classes='folder label')
            yield Link("Open Folder via SFTP", url=self.ftp_link, id="ftp-link", classes='focusable folder link')
            yield Container(Button("Back", id="back", classes='focusable folder button'), id='folder-button-container')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

    def action_back(self):
        self.dismiss()
