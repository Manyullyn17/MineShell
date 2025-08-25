import unicodedata, re, httpx, aiofiles
from datetime import datetime
from pathlib import Path
from config import DATE_FORMAT
from textual.widgets import Select
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
    BINDINGS = [
        Binding(
            "enter,space",
            "show_overlay",
            "Show menu",
            show=False,
        )
    ]

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
