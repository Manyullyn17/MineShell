from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalGroup
from textual.widgets import Button

from helpers import CustomModal

class ContextMenu(CustomModal[str]):
    CSS_PATH = 'styles/context_menu.tcss'

    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
            Binding('up', "focus_move('up')", show=False),
            Binding('down', "focus_move('down')", show=False),
        ]

    def __init__(self, pos: tuple[int, int], options: list[str]) -> None:
        super().__init__()
        self.pos = pos  # (x, y)
        self.options = options
        self.pos_offset = 1
        self.add_class('context-modal')

    def compose(self) -> ComposeResult:
        self.styles.align = ('left', 'top')
        self.menu = VerticalGroup(id="context-menu", classes="context-menu")
        with self.menu:
            for option in self.options:
                yield Button(option.replace('-', ' ').title(), id=f"context-{option}", compact=True)

    def on_mount(self) -> None:
        # Position menu where the click happened
        self.menu.styles.offset = (self.pos[0], self.pos[1] + self.pos_offset)
        self.query_one(Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(str(event.button.id).removeprefix('context-'))  # return selection

    def action_focus_move(self, direction) -> None:
        if direction == 'down':
            self.focus_next()
        elif direction == 'up':
            self.focus_previous()

    def action_back(self):
        self.dismiss()
