import unicodedata, re, httpx, aiofiles
from datetime import datetime
from pathlib import Path
from typing import TypeVar
from config import DATE_FORMAT
from textual import on
from textual.events import MouseDown
from textual.widget import Widget
from textual.widgets import Select, Input, DataTable
from textual.screen import ModalScreen
from textual.binding import Binding

def format_date(iso_string: str, format: str=DATE_FORMAT) -> str:
    """Convert an ISO8601 datetime string (from Mojang API) into the global DATE_FORMAT."""
    # Mojang uses trailing Z for UTC, Python needs +00:00
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime(format)

def sanitize_filename(text: str) -> str:
    # Normalize Unicode characters to closest ASCII equivalent
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

    # Replace spaces with underscores
    text = text.replace(' ', '_')

    # Remove any remaining invalid characters
    text = re.sub(r'[^\w\-_.]', '', text)

    return text

async def download_file(url: str, dest: Path, progress_cb=None, step=None, cancel_event=None):
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0
            async with aiofiles.open(dest, "wb") as f:
                async for chunk in resp.aiter_bytes(16384):
                    if cancel_event and cancel_event.is_set():
                        return
                    await f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(total, downloaded, step=step)


class CustomSelect(Select):
    def on_key(self, event):
        """Override to prevent up/down from opening the menu."""
        if event.key in ("up", "down") and not self.expanded:
            # Let the default navigation work, but don’t trigger menu opening
            screen = self.app.screen
            if hasattr(screen, "action_focus_move"):
                getattr(screen, "action_focus_move")(event.key)
            event.stop()
            return
        # Fallback to normal Select behavior
        return super()._on_key(event)

class SmartInput(Input):
    def on_key(self, event):
        if event.key in ("left", "right"):
            # Determine if we should move focus
            move_focus = (
                (event.key == "left" and self.cursor_at_start) or
                (event.key == "right" and self.cursor_at_end)
            )

            if move_focus:
                # Call the screen's focus movement
                screen = self.app.screen
                if hasattr(screen, "action_focus_move"):
                    getattr(screen, "action_focus_move")(event.key)
                event.stop()
                return

        # fallback to normal Input behavior
        return super()._on_key(event)

class CustomTable(DataTable):
    BINDINGS = [
        Binding(
            "enter,space",
            "show_overlay",
            "Show menu",
            show=False,
        )
    ]

    def on_key(self, event):
        """Override to make up/down move focus if top or bottom row is selected."""
        if event.key in ("up", "down") and self.cursor_type == 'row':
            # Determine if we should move focus
            move_focus = (
                (event.key == "up" and self.cursor_row == 0) or
                (event.key == "down" and self.cursor_row == len(self.rows)-1)
            )

            if move_focus:
                # Call the screen's focus movement
                screen = self.app.screen
                if hasattr(screen, "action_focus_move"):
                    getattr(screen, "action_focus_move")(event.key)
                event.stop()
                return
        if event.key == 'enter':
            super()._post_selected_message()
        # Fallback to normal DataTable behavior
        return super()._on_key(event)

ScreenResultType = TypeVar("ScreenResultType")

class CustomModal(ModalScreen[ScreenResultType]):
    main_widget: Widget | None = None
    allow_click_outside: bool = True  # default behavior

    @on(MouseDown)
    def on_mouse_click(self, event: MouseDown):
        if not self.allow_click_outside:
            return  # ignore clicks outside

        widget = self.get_main_widget()
        if not widget or not widget.styles.height or not widget.styles.width:
            return

        w = widget.styles.width.value or 0
        h = widget.styles.height.value or 0
        if w == 0 or h == 0:
            return

        screen_w, screen_h = self.size
        left = (screen_w - w) // 2
        right = (screen_w + w) // 2 - 1
        top = (screen_h - h) // 2
        bottom = (screen_h + h) // 2 - 1

        mx, my = event.screen_x, event.screen_y
        if mx < left or mx > right or my < top or my > bottom:
            self.dismiss()

    def get_main_widget(self) -> Widget | None:
        if self.main_widget:
            return self.main_widget
        
        # pick first non-system child
        for child in self.children:
            if "-textual-system" not in child.classes:
                return child

        return None
