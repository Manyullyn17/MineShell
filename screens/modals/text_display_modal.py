from textual import on
from textual.binding import Binding
from textual.containers import Grid
from textual.events import Resize
from textual.widgets import Button, Static
from rich.markdown import Markdown

from helpers import CustomModal, FocusNavigationMixin, CustomVerticalScroll

class TextDisplayModal(FocusNavigationMixin, CustomModal[str | None]):
    """General-purpose scrollable text modal.

    Args:
        title: Title shown at the top.
        text: Text/markdown to display.
        fixed_width (default: 0 -> auto): Modal content width (cols/ch units).
        fixed_height (default: 0 -> auto): Modal content height (rows/ch units).
        markdown (default: True): If True, render using Rich Markdown.
    """
    CSS_PATH = 'styles/text_display_modal.tcss'
    BINDINGS = [
        ("q", "back", "Back"),
        Binding('escape', 'back', show=False),
    ] + FocusNavigationMixin.BINDINGS

    def __init__(self, title: str, text: str, fixed_width: int = 0, fixed_height: int = 0, markdown: bool = True) -> None:
        super().__init__()
        self._title = title
        self._text = text
        self.fixed_width = fixed_width
        self.fixed_height = fixed_height
        self._markdown = markdown
        self.longest = 0
        self.lines = 0
        for line in self._text.splitlines():
            self.lines += 1
            if len(line) > self.longest:
                self.longest = len(line)

    def compose(self):
        # content widget (either Markdown or wrapped Static)
        content = (
            Static(Markdown(self._text), id="tdm-content", expand=True)
            if self._markdown
            else Static(self._text, id="tdm-content", expand=True)
        )

        self.grid = Grid(id="tdm-grid")

        with self.grid:
            yield CustomVerticalScroll(content, allow_scroll=True, id="tdm-scroll", classes='tdm scroll focusable')
            yield Button("Close", id="tdm-close", classes='tdm button focusable')

    def on_mount(self):
        if self.fixed_width:
            self.grid.styles.width = self.fixed_width
        if self.fixed_height:
            self.grid.styles.height = self.fixed_height
        self.grid.border_title = self._title
        # focus the scroll view so the mouse wheel / arrows work immediately
        self.query_one("#tdm-scroll").focus()

    @on(Resize)
    def on_resize(self, event: Resize):
        if not self.fixed_width:
            self.grid.styles.width = max(min(int(self.size.width * 0.8), self.longest + 12), 10) # size = len(longest_line) + 12, max = screenwidth * 80%, min = 10
        if not self.fixed_height:
            self.grid.styles.height = max(min(int(self.size.height * 0.8), self.lines + 10), 10) # size = count(lines) + 10, max = screenwidth * 80%, min = 10

    def action_back(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "tdm-close":
            self.dismiss(None)
