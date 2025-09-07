from textual.events import Resize
from textual.widgets import DataTable
from textual.app import ComposeResult
from textual.binding import Binding
from screens.modals import FilterModal
from helpers import CustomModal

class ModBrowserModal(CustomModal[str]):
    CSS_PATH = 'styles/modbrowser_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
            Binding('f', 'filter', 'Filter', show=True),
            Binding('r', 'reset', 'Reset', show=True),
        ]

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        ...

    def on_mount(self):
        ...

    def _on_resize(self, event: Resize):

        return super()._on_resize(event)

    def action_back(self):
        self.dismiss()
