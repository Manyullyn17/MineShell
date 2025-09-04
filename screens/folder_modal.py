from textual import on
from textual.events import MouseDown
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
        self.grid = Grid(id='dialog')
        with self.grid:
            yield Static("Instance: ", classes='folder static')
            yield Label(f"{self.instance_name}", id="instance-name", classes='folder label')
            yield Static("Folder Path:", classes='folder static')
            yield Label(f"{self.folder_path}", id="folder-path", classes='folder label')
            yield Link("Open Folder via SFTP", url=self.ftp_link, id="ftp-link", classes='folder link')
            yield Container(Button("Back", id="back", classes='folder button'), id='folder-button-container')

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

    @on(MouseDown)
    def on_mouse_click(self, event: MouseDown):
        width, height = self.size
        if not self.grid.styles.width or not self.grid.styles.height:
            return
        m_width = self.grid.styles.width.value
        m_height = self.grid.styles.height.value

        mouse_x = event.screen_x
        mouse_y = event.screen_y

        if (mouse_x < (width - m_width) // 2 or mouse_x > (width + m_width) // 2
            or mouse_y < (height - m_height) // 2 or mouse_y > (height + m_height) // 2):
            self.dismiss()
