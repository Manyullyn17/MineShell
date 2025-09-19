from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static

from widgets import CustomList, Card

class ModCard(Card):
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

    can_focus = True
    is_selected = reactive(False)

    def __init__(self, mod: dict | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mod = mod or {}
        self.classes = "modcard"

    def compose(self):
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

class ModList(CustomList):
    """Container for multiple mod cards."""
    def __init__(self, placeholder_count: int = 5, *args, **kwargs):
        super().__init__(placeholder_count, *args, **kwargs)

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
