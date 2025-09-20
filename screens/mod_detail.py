import asyncio

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, TabbedContent, TabPane, Static, Button
from rich.markdown import Markdown

from backend.api import SourceAPI, ModrinthAPI, CurseforgeAPI

from helpers import FocusNavigationMixin, strip_images, CustomVerticalScroll

class ModDetailScreen(FocusNavigationMixin, Screen):
    CSS_PATH = 'styles/mod_detail_screen.tcss'
    BINDINGS = [
        Binding('q', "back", "Back", show=True),
        Binding('escape', "back", "Back", show=False),
    ] + FocusNavigationMixin.BINDINGS

    sources = {
        "modrinth": ModrinthAPI(),
        "curseforge": CurseforgeAPI(),
    }

    def __init__(self, mod: dict, source: str, sub_title: str) -> None:
        super().__init__()
        self.mod = mod
        # mod: name, author, downloads, modloader, categories, description (short description), type, client_side, server_side
        self.source = source
        self.source_api: SourceAPI = self.sources[self.source]
        self.sub_title = sub_title + f' > {mod.get('name', '')}'

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal(classes='mod-detail header'):
            yield Static(self.mod.get('name', ''), classes='mod-detail name')
            yield Static(f'by {self.mod.get('author', '')}', classes='mod-detail author')
            yield Static(classes='mod-detail header spacer')
            yield Static(f'Downloads: {self.mod.get("downloads", 0)}', classes='mod-detail downloads')

        with TabbedContent(classes='focusable'):
            with TabPane('Description'):
                self.description_label =  Label(expand=True, classes='mod-detail description text')
                self.set_label_loading(self.description_label, True)
                yield CustomVerticalScroll(self.description_label, allow_scroll=True, classes='mod-detail description scroll focusable')
            with TabPane('Versions'):
                yield Label('Versions')
                yield Button('test', classes='focusable')
                yield Button('test2', classes='focusable')
                yield Button('test3', classes='focusable')

        yield Footer()

    async def on_mount(self):
        self.get_mod_info()

    @work(thread=True)
    async def get_mod_info(self):
        # - load version info only when opening versions tab? or preload them at the start? maybe not both at once so mod_info gets used immediately and doesn't wait for versions
        self.mod_info, self.mod_versions = await asyncio.gather(self.source_api.get_mod(str(self.mod.get('project_id'))), self.source_api.get_mod_versions(str(self.mod.get('project_id'))))
        # mod_info: published, updated
        # mod_versions: id, name, version_number, changelog, date_published, downloads, version_type, files[url, filename, primary]
        body = strip_images(self.mod_info.get('body', ''))
        self.call_later(self.update_markdown_label, self.description_label, body)
        # - show stuff once done

    def update_markdown_label(self, label: Label, text):
        label.update(Markdown(text))
        self.set_label_loading(label, False)

    def set_label_loading(self, label: Label, loading: bool):
        label.loading = loading
        label.styles.height = '1fr' if loading else 'auto'

    def action_back(self):
        self.dismiss()
