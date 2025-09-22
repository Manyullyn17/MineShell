from textual.binding import Binding
from textual.events import Key, Enter, Leave, Focus, Blur
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, LoadingIndicator

from helpers import CustomVerticalScroll

class PlaceholderCard(Static):
    """A placeholder card that's used for loading."""
    DEFAULT_CSS = """
    PlaceholderCard {
        border: solid $accent-darken-1;
        padding: 0;
        margin: 1;
        background: $surface;
        height: 10;
    }

    PlaceholderCard.card-loading-indicator {
        background: $panel-darken-1;
        color: $accent;
        height: 1fr;
        width: 1fr;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classes = "placeholdercard"
        self.disabled = True

    def compose(self):
        yield LoadingIndicator(classes='card-loading-indicator')

class Card(Static):
    """A single card that displays stuff and is selectable."""
    BINDINGS = [
        Binding("enter", "enter", priority=True),
        Binding("left", "move_focus('left')", priority=True),
        Binding("right", "move_focus('right')", priority=True),
    ]

    DEFAULT_CSS = """
    Card {
        border: solid $accent-darken-1;
        padding: 1 2 0 2;
        margin: 1;
        background: $surface;
        height: 10;
    }
        
    Card.selected {
        border: double $accent-lighten-1;
        background: $boost;
    }

    Card.hovered {
        background: $boost;
    }
    """

    class Selected(Message):
        """Posted when the card is clicked/selected."""
        def __init__(self, sender: "Card", item: dict) -> None:
            super().__init__()
            self.item = item
            self.sender = sender

    _switched_focus = False
    can_focus = True
    is_selected = reactive(False)

    def __init__(self, item: dict | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = item or {}
        self.classes = "card"

    def on_click(self) -> None:
        self.post_message(self.Selected(self, self.item))

    def action_enter(self):
        self.on_click()

    def on_enter(self, event: Enter) -> None:
        self.set_class(self.is_mouse_over, "hovered")

    def action_move_focus(self, direction: str):
        def base_action(self, direction: str):
            if hasattr(self.screen, 'action_focus_move'):
                self.is_selected = False
                getattr(self.screen, 'action_focus_move')(direction)
        
        if self.screen.focused == self and direction != 'left':
            focused = self
        else:
            for child in self.walk_children():
                if isinstance(child, Widget) and child.has_focus:
                    focused = child
                    break
            else:
                base_action(self, direction)
                return
        
        ref_x = focused.region.x if direction == 'right' else focused.region.right

        candidates = [w for w in self.walk_children() if isinstance(w, Widget) and w.can_focus and w is not self]

        if direction == 'right':
            candidates = [w for w in candidates if w.region.x > ref_x]
        else:
            candidates = [w for w in candidates if w.region.right < ref_x]

        if not candidates:
            if focused is not self:
                self.focus()
            else:
                base_action(self, direction)
            return
        
        if direction == 'right':
            next_widget = min(candidates, key=lambda w: w.region.x)
        else:
            next_widget = max(candidates, key=lambda w: w.region.right)
        
        next_widget.focus()
        self.is_selected = True
        self._switched_focus = True

    def on_leave(self, event: Leave) -> None:
        self.set_class(self.is_mouse_over, "hovered")

    def on_focus(self, event: Focus) -> None:
        if event.from_app_focus:
            return
        self.is_selected = True

    def on_blur(self, event: Blur) -> None:
        if not self._switched_focus:
            self.is_selected = False
        else:
            self._switched_focus = False

    def watch_is_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")

class CustomList(CustomVerticalScroll):
    """Container for multiple cards."""

    class Selected(Message):
        """Posted when a mod card is selected."""
        def __init__(self, sender: "CustomList", item: dict) -> None:
            super().__init__()
            self.item = item
            self.sender = sender

    custom_loading = reactive(False)

    def __init__(self, placeholder_count: int = 5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cards: list[Card] = []
        self.loading_cards: list[PlaceholderCard] = []
        self.index = 0
        for _ in range(placeholder_count):
            card = PlaceholderCard(classes='loading-card')
            self.loading_cards.append(card)

    def on_mount(self):
        for card in self.loading_cards:
            self.mount(card)

    def on_key(self, event: Key):
        """Override to make ModList scroll up and down and release focus if reaching either end"""
        if event.key not in ('up', 'down'):
            return super().on_key(event)

        self.cards[self.index].is_selected = False

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

    def set_cards(self, items: list[dict]):
        self.cards.clear()
        self.remove_children('.card')
        self.index = 0
        self.add_cards(items)

    def add_cards(self, items: list[dict]):
        for item in items:
            card = Card(item, classes='card')
            self.cards.append(card)
            self.mount(card)
        self.custom_loading = False

    def on_card_selected(self, event: Card.Selected) -> None:
        self.index = self.cards.index(event.sender)
        # Deselect others
        for card in self.cards:
            card.is_selected = False
        event.sender.is_selected = True
        event.stop()
        self.post_message(self.Selected(self, event.item))

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

