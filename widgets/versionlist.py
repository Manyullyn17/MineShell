from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static, Button

from widgets import CustomList, Card
from helpers import format_date

class VersionCard(Card):
    """A single version card that displays version info and is selectable."""
    DEFAULT_CSS = """
    VersionCard {
        border: solid $accent-darken-1;
        # padding: 1 2 0 2;
        padding: 0 2 0 2;
        margin: 1;
        background: $surface;
        # height: 10;
        height: 6;

        .spacer {
            width: 1fr;
        }

        .header {
            height: 2;

            .name {
                width: auto;
                color: $accent-lighten-1;
            }

            .date {
                width: auto;
                color: $foreground-darken-2;
                padding-left: 1;
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
                height: 1;
                width: auto;
            }

            .gameversions {
                content-align: left middle;
                height: 1;
                width: auto;
            }
        }
    }

    VersionCard.selected {
        border: double $accent-lighten-1;
        background: $boost;
    }

    VersionCard.hovered {
        background: $boost;
    }

    VersionCard.versioncard-loading-indicator {
        background: $panel-darken-1;
        color: $accent;
        height: 1fr;
        width: 1fr;
    }
    """

    can_focus = True
    is_selected = reactive(False)

    def __init__(self, version: dict | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = version or {}
        self.classes = "versioncard"
        try:
            self.date_published = format_date(self.item.get('date_published', ''))
        except ValueError:
            self.date_published = 'Unknown'

    def compose(self):
        with Horizontal(classes="versioncard header"):
            yield Static(self.item.get("name", "Unknown"), classes="versioncard header name")
            yield Static(f'- {self.date_published}', classes="versioncard header date")
            yield Static(classes='versioncard header spacer')
            yield Static(f"Downloads: {self.item.get('downloads', 0):,}", classes="versioncard header downloads")
        with Horizontal(classes="versioncard tags"):
            with Vertical():
                yield Static(", ".join(self.item.get("loaders", [])).title(), classes="versioncard tags loaders")
                yield Static(", ".join(self.item.get("game_versions", [])), classes="versioncard tags gameversions")
            yield Static(classes='versioncard tags spacer')
            yield Button('Changelog', compact=True, classes='versioncard button focusable')
            yield Button('Install', compact=True, classes='versioncard button focusable')
        self.border_subtitle = self.item.get('version_type', '').title()

class VersionList(CustomList):
    """Container for multiple version cards."""
    DEFAULT_CSS = """
    VersionList {
        PlaceholderCard {
            height: 6;
        }
    }
    """
    def __init__(self, placeholder_count: int = 5, *args, **kwargs):
        super().__init__(placeholder_count, *args, **kwargs)

    def set_versions(self, versions: list[dict]):
        self.cards.clear()
        self.remove_children('.card')
        self.index = 0
        self.add_versions(versions)

    def add_versions(self, versions: list[dict]):
        for version in versions:
            card = VersionCard(version, classes='card')
            self.cards.append(card)
            self.mount(card)
        self.custom_loading = False
