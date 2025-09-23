from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.widgets import Button, Label

from helpers import CustomModal, NavigationMixin

class DeleteModal(NavigationMixin,CustomModal[bool]):
    CSS_PATH = 'styles/delete_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False)
        ] + NavigationMixin.BINDINGS
    
    def __init__(self, title: str='Delete Instance?'):
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        self.grid = Grid(id='delete-dialog')
        with self.grid:
            yield Label(f'{self.title}', id='question')
            yield Button('Yes', variant='primary', id='yes', classes='focusable')
            yield Button('No', variant='error', id='no', classes='focusable')

    def on_mount(self) -> None:
        self.query_one('#no', expect_type=Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'yes':
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_back(self):
        self.app.pop_screen()

