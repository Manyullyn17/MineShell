from textual import events
from textual.app import ComposeResult
from textual.widgets import Button, Label
from textual.containers import Grid
from textual.binding import Binding
from helpers import CustomModal

class DeleteModal(CustomModal[bool]):
    CSS_PATH = 'styles/delete_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False)
        ]
    
    def __init__(self, title: str='Delete Instance?'):
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        self.grid = Grid(id='delete-dialog')
        with self.grid:
            yield Label(f'{self.title}', id='question')
            yield Button('Yes', variant='primary', id='yes')
            yield Button('No', variant='error', id='no')

    def on_mount(self) -> None:
        self.query_one('#no', expect_type=Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'yes':
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event: events.Key):
        if not self.focused:
            return
        
        if event.key == 'right':
            self.focus_next()
            event.stop()
        elif event.key == 'left':
            self.focus_previous()
            event.stop()

    def action_back(self):
        self.app.pop_screen()

