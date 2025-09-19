from textual.containers import Horizontal
from textual.events import Key, Enter, Leave, Focus, Blur
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static, LoadingIndicator

from helpers import CustomVerticalScroll

class ModCard(Static):
    """A single mod card that displays mod info and is selectable."""
    DEFAULT_CSS = """
    ModCard {
        border: solid $accent-darken-1;
        padding: 1 2 0 2;
        margin: 1;
        background: $surface;
        height: 10;

        .spacer {
            width: 1fr;
        }

        .header {
            height: 2;

            .name {
                width: auto;
                color: $accent-lighten-1;
            }

            .author {
                width: auto;
                color: $foreground-darken-2;
            }

            .downloads {
                width: auto;
            }
        }

        .description {
            height: 1fr;
        }

        .tags {
            .loaders {
                content-align: left middle;
                height: 1fr;
                width: auto;
            }

            .categories {
                content-align: left middle;
                height: 1fr;
                width: auto;
            }
        }
    }

    ModCard.selected {
        border: double $accent-lighten-1;
        background: $boost;
    }

    ModCard.hovered {
        background: $boost;
    }

    ModCard.modcard-loading-indicator {
        background: $panel-darken-1;
        color: $accent;
        height: 1fr;
        width: 1fr;
    }
    """

    class Selected(Message):
        """Posted when the card is clicked/selected."""
        def __init__(self, sender: "ModCard", mod: dict) -> None:
            super().__init__()
            self.mod = mod
            self.sender = sender

    can_focus = True
    is_selected = reactive(False)

    def __init__(self, mod: dict | None = None, loading: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mod = mod or {}
        self.loading_placeholder = loading
        self.classes = "modcard"

    def compose(self):
        if not self.loading_placeholder:
            with Horizontal(classes="modcard header"):
                yield Static(self.mod.get("name", "Unnamed"), classes="modcard header name")
                yield Static(f" by {self.mod.get('author', 'Unknown')}", classes="modcard header author")
                yield Static(classes='modcard header spacer')
                yield Static(f"Downloads: {self.mod.get('downloads', 0)}", classes="modcard header downloads")
            yield Static(self.mod.get("description", ""), classes="modcard description")
            with Horizontal(classes="modcard tags"):
                yield Static(", ".join(self.mod.get("modloader", [])), classes="modcard tags loaders")
                yield Static(classes='modcard tags spacer')
                yield Static(", ".join(self.mod.get("categories", [])), classes="modcard tags categories")
            self.border_subtitle = ", ".join(self.mod.get('type', '')).title()
        else:
            yield LoadingIndicator(classes='modcard-loading-indicator')
            self.disabled = True

    def on_click(self) -> None:
        self.post_message(self.Selected(self, self.mod))

    def on_enter(self, event: Enter) -> None:
        self.set_class(self.is_mouse_over, "hovered")

    def on_leave(self, event: Leave) -> None:
        self.set_class(self.is_mouse_over, "hovered")

    def on_focus(self, event: Focus) -> None:
        if event.from_app_focus:
            return
        self.is_selected = True

    def on_blur(self, event: Blur) -> None:
        self.is_selected = False

    def watch_is_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")

class ModList(CustomVerticalScroll):
    """Container for multiple mod cards."""

    class Selected(Message):
        """Posted when a mod card is selected."""
        def __init__(self, sender: "ModList", mod: dict) -> None:
            super().__init__()
            self.mod = mod
            self.sender = sender

    custom_loading = reactive(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cards: list[ModCard] = []
        self.loading_cards: list[ModCard] = []
        self.index = 0

    def on_mount(self):
        for _ in range(5):
            card = ModCard(loading=True, classes='loading-card')
            self.loading_cards.append(card)
            self.mount(card)

    def on_key(self, event: Key):
        """Override to make ModList scroll up and down and release focus if reaching either end"""
        if event.key not in ('up', 'down'):
            return super().on_key(event)

        # Determine the new index
        new_index = self.index - 1 if event.key == 'up' else self.index + 1

        # If we're within bounds, move focus
        if 0 <= new_index < len(self.cards):
            self.index = new_index
            self.focus_card(self.index)
            event.stop()
            event.prevent_default()
        else:
            # At the boundary, defer to the normal handler
            return super().on_key(event)

    def on_focus(self, event: Focus):
        self.focus_card(self.index)
        event.stop()

    def focus_card(self, index: int):
        self.cards[index].focus()

    def set_mods(self, mods: list[dict]):
        self.cards.clear()
        self.remove_children('.card')
        self.index = 0
        self.add_mods(mods)

    def add_mods(self, mods: list[dict]):
        for mod in mods:
            card = ModCard(mod, classes='card')
            self.cards.append(card)
            self.mount(card)
        self.custom_loading = False

    def on_mod_card_selected(self, event: ModCard.Selected) -> None:
        self.index = self.cards.index(event.sender)
        # Deselect others
        for card in self.cards:
            card.is_selected = False
        event.sender.is_selected = True
        event.stop()
        self.post_message(self.Selected(self, event.mod))

    def watch_custom_loading(self, loading: bool) -> None:
        self.scroll_home(animate=False, immediate=True)
        self.disabled = loading
        self.show_cards(loading)

    def show_cards(self, loading: bool = False) -> None:
        if not loading:
            for card in self.loading_cards:
                card.add_class('hidden')
            for card in self.cards:
                card.remove_class('hidden')
        else:
            for card in self.loading_cards:
                card.remove_class('hidden')
            for card in self.cards:
                card.add_class('hidden')
