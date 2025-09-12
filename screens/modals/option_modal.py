from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from helpers import CustomModal

class OptionModal(CustomModal[str]):
    CSS_PATH = 'styles/option_modal.tcss'

    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
        ]

    def __init__(self, options: list[str | tuple[str, bool]], pos: tuple[int, int] | None = None) -> None:
        """
        Opens a modal with a list of selectable options.

        Args:
            options : list of str or tuple[str, bool]\n
                Each item represents an option.
                - If a string: the option is enabled by default.
                - If a tuple: the first element is the option value,
                the second element is a boolean indicating if the option
                is disabled.

                Example:
                    options = [
                        "option1",          # enabled by default
                        ("option2", True),  # disabled
                    ]
            pos : tuple[x_pos, y_pos] | None\n
                The position of the modal. If None, the modal is centered.\n
                Coordinates start from the top-left.
        Returns:
            str
                The value of the selected option.
        """
        super().__init__()
        self.pos = pos  # (x, y)
        self.options = [(value, False) if isinstance(value, str) else value for value in options]
        self.pos_offset = 1
        self.add_class('context-modal')

    def compose(self) -> ComposeResult:
        self.menu = OptionList(*[Option(option.replace('_', ' ').title(), id=option, disabled=disabled) for option, disabled in self.options], id="context-menu", classes="context-menu")
        yield self.menu

    def on_mount(self) -> None:
        # Position menu where the click happened if pos is set
        if self.pos:
            self.styles.align = ('left', 'top')
            self.menu.styles.offset = (self.pos[0], self.pos[1] + self.pos_offset)
        else:
            self.styles.align = ('center', 'middle')

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.id))

    def action_back(self):
        self.dismiss()
