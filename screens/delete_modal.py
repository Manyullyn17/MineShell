from textual import events
from textual.app import ComposeResult
from textual.widgets import Button, Label
from textual.screen import ModalScreen
from textual.containers import Grid
from textual.binding import Binding

class DeleteModal(ModalScreen[bool]):
    CSS_PATH = 'styles/delete_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False)
        ]
    
    def __init__(self, title: str='Delete Instance?'):
        super.__init__
        self.title = title

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f'{self.title}', id='question'),
            Button('Yes', variant='primary', id='yes'),
            Button('No', variant='error', id='no'),
            id='delete-dialog'
        )

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

