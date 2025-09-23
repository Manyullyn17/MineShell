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
        padding: 0 2 0 2;
        margin: 1;
        background: $surface;
        height: 6;

        .spacer {
            width: 1fr;
        }

        .button {
            background: $background-lighten-1;
            margin: 0 1;
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

    VersionCard.release {
        border-subtitle-color: $success;
    }

    VersionCard.beta {
        border-subtitle-color: $warning;
    }

    VersionCard.alpha {
        border-subtitle-color: $error;
    }
    """

    can_focus = True
    is_selected = reactive(False)

    def __init__(self, version: dict | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = version or {}
        self.classes = f"{' '.join(self.classes)} versioncard {self.item.get('version_type', '').lower()}"

    def compose(self):
        with Horizontal(classes="versioncard header"):
            yield Static(self.item.get("name", "Unknown"), classes="versioncard header name")
            yield Static(f'- {format_date(self.item.get('date_published', ''))}', classes="versioncard header date")
            yield Static(classes='versioncard header spacer')
            yield Static(f"Downloads: {self.item.get('downloads', 0):,}", classes="versioncard header downloads")
        with Horizontal(classes="versioncard tags"):
            with Vertical():
                yield Static(", ".join(self.item.get("loaders", [])).title(), classes="versioncard tags loaders")
                yield Static(", ".join(self.item.get("game_versions", [])), classes="versioncard tags gameversions")
            yield Static(classes='versioncard tags spacer')
            yield Button('Changelog', compact=True, id='changelog', classes='versioncard button focusable')
            yield Button('Install', compact=True, id='install', classes='versioncard button focusable')
        self.border_subtitle = self.item.get('version_type', '').title()

class VersionList(CustomList):
    """Container for multiple version cards."""
    DEFAULT_CSS = """
    VersionList {
        PlaceholderCard {
            height: 6;
        }
        .static-placeholder {
            content-align: center middle;
            height: 5;
            width: 1fr;
            outline: heavy $panel;
            margin: 0 1 1 1;
        }
    }
    """
    
    def __init__(self, placeholder_count: int = 5, *args, **kwargs):
        super().__init__(placeholder_count, *args, **kwargs)
        self.all_cards = []

    def set_versions(self, versions: list[dict], filter: dict = {}):
        self.all_cards.clear()
        self.remove_children('.card')
        self.remove_children('.static-placeholder')
        self.index = 0
        self.add_versions(versions, filter)

    def add_versions(self, versions: list[dict], filter: dict = {}):
        for version in versions:
            card = VersionCard(version, classes='card')
            self.all_cards.append(card)
            if not filter:
                self.mount(card)
        if filter:
            self.filter_versions(filter)
        self.custom_loading = False

    def filter_versions(self, filter: dict):
        def matches(item: dict) -> bool:
            for key, allowed in filter.items():
                value = item.get(key, None)

                # If no filters for this key, skip
                if not allowed:
                    continue

                # Value can be a string or a list of strings
                if isinstance(value, list):
                    # At least one match in the list
                    if not any(v in allowed for v in value):
                        return False
                else:
                    # Simple string match
                    if value not in allowed:
                        return False
            return True
        
        self.custom_loading = True
        self.remove_children('.card')
        self.remove_children('.static-placeholder')

        capped = False
        self.cards.clear()
        for v in self.all_cards:
            if matches(v.item):
                self.cards.append(VersionCard(v.item))
                if len(self.cards) >= 50:
                    capped = True
                    break
        if self.cards:
            self.mount_all(self.cards)
        else:
            self.mount(Static('No results.', classes=f'versionlist static-placeholder'))
        if capped:
            self.mount(Static('Results capped for performance.', classes=f'versionlist static-placeholder'))
        self.custom_loading = False
