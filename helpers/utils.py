import unicodedata, re, httpx, aiofiles
from pathlib import Path
from datetime import datetime
from typing import Literal

from config import DATE_FORMAT

ModloaderType = Literal["fabric", "forge", "neoforge", "quilt"]

def format_date(iso_string: str, format: str=DATE_FORMAT) -> str:
    """Convert an ISO8601 datetime string into the global DATE_FORMAT."""
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

    return text.lower()

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

def strip_images(text: str) -> str:
    # remove HTML <img ...> tags
    text = re.sub(r'<img[^>]*>', '[image removed]', text)
    # remove Markdown images ![alt](url)
    text = re.sub(r'!\[.*?\]\(.*?\)', '[image removed]', text)
    return text
