from typing import TypeVar

from textual import on
from textual.events import MouseDown
from textual.screen import ModalScreen
from textual.widget import Widget

ScreenResultType = TypeVar("ScreenResultType")

class CustomModal(ModalScreen[ScreenResultType]):
    main_widget: Widget | None = None
    allow_click_outside: bool = True  # default behavior

    @on(MouseDown)
    def on_mouse_down(self, event: MouseDown):
        if not self.allow_click_outside:
            return  # ignore clicks outside

        widget = self.get_main_widget()
        if not widget or not widget.styles.height or not widget.styles.width:
            return

        w = widget.styles.width.value or 0
        h = widget.styles.height.value or 0
        if w == 0 or h == 0:
            return

        x, y, width, height = self.find_widget(widget).region
        left = x
        right = x + width - 1
        top = y
        bottom = y + height - 1

        mx, my = event.screen_x, event.screen_y
        if not (left <= mx <= right and top <= my <= bottom):
            self.dismiss()

    def get_main_widget(self) -> Widget | None:
        if self.main_widget:
            return self.main_widget
        
        # pick first non-system child
        for child in self.children:
            if "-textual-system" not in child.classes:
                return child

        return None
