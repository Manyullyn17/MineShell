from textual import events, on
from textual.events import MouseDown
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
