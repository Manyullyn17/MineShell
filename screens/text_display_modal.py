from textual.screen import ModalScreen
from textual.containers import Grid, VerticalScroll
from textual.widgets import Label, Button, Static
from textual.binding import Binding
from rich.markdown import Markdown

class TextDisplayModal(ModalScreen[str | None]):
    """General-purpose scrollable text modal.

    Args:
        title: Title shown at the top.
        text: Text/markdown to display.
        width: Modal content width (cols/ch units).
        height: Modal content height (rows/ch units).
        markdown: If True, render using Rich Markdown.
    """
    CSS_PATH = 'styles/text_display_modal.tcss'
    BINDINGS = [
        ("q", "back", "Back"),
        Binding('escape', 'back', show=False),
    ]

    def __init__(
        self,
        title: str,
        text: str,
        *,
        width: int = 0,
        height: int = 0,
        markdown: bool = True
    ) -> None:
        super().__init__()
        self._title = title
        self._text = text
        self._width = width
        self._height = height
        self._markdown = markdown

    def compose(self):
        # content widget (either Markdown or wrapped Static)
        content = (
            Static(Markdown(self._text), id="tdm-content", expand=True)
            if self._markdown
            else Static(self._text, id="tdm-content", expand=True)
        )

        yield Grid(
            Label(self._title, id="tdm-title"),
            VerticalScroll(content, id="tdm-scroll"),
            Button("Close", id="tdm-close"),
            id="tdm-grid"
        )

    def on_mount(self):
        grid = self.query_one("#tdm-grid")
        if self._width:
            grid.styles.width = self._width
        if self._height:
            grid.styles.height = self._height

        # focus the scroll view so the mouse wheel / arrows work immediately
        self.query_one("#tdm-scroll").focus()

    def action_back(self):
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "tdm-close":
            self.dismiss(None)
