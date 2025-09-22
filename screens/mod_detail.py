from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, TabbedContent, TabPane, Static, Button
from rich.markdown import Markdown

from backend.api import SourceAPI, ModrinthAPI, CurseforgeAPI
from backend.api.mojang import get_minecraft_versions
from backend.storage import InstanceConfig

from helpers import FocusNavigationMixin, strip_images, CustomVerticalScroll
from widgets import FilterSidebar, VersionList

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

    def __init__(self, mod: dict, source: str, sub_title: str, instance: InstanceConfig) -> None:
        super().__init__()
        self.mod = mod
        self.source = source
        self.source_api: SourceAPI = self.sources[self.source]
        self.sub_title = sub_title + f' > {mod.get('name', '')}'
        self.instance = instance
        self.modloader = instance.modloader
        self.mc_version = instance.minecraft_version

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal(classes='mod-detail header'):
            yield Static(self.mod.get('name', ''), classes='mod-detail name')
            yield Static(f'by {self.mod.get('author', '')}', classes='mod-detail author')
            yield Static(classes='mod-detail header spacer')
            yield Static(f'Downloads: {self.mod.get("downloads", 0)}', classes='mod-detail downloads')

        with TabbedContent(classes='focusable'):
            with TabPane('Description'):
                with Horizontal(classes='mod-detail description'):
                    self.description_label =  Label(expand=True, classes='mod-detail description text')
                    self.set_label_loading(self.description_label, True)
                    yield CustomVerticalScroll(self.description_label, allow_scroll=True, classes='mod-detail description scroll focusable')

                    with Vertical(classes='mod-detail description info'):
                        yield Static('Loaders:', classes='mod-detail description info static')
                        yield Label(f'{', '.join(self.mod.get("modloader", ""))}', classes='mod-detail description info label')
                        yield Static('Categories:', classes='mod-detail description info static')
                        yield Label(f'{', '.join(self.mod.get("categories", ""))}', classes='mod-detail description info label')
                        yield Static('Type:', classes='mod-detail description info static')
                        yield Label(f'{', '.join(self.mod.get("type", "")).title()}', classes='mod-detail description info label')
                        yield Static('Client Side:', classes='mod-detail description info static')
                        yield Label(f'{self.mod.get("client_side", "").title()}', classes='mod-detail description info label')
                        yield Static('Server Side:', classes='mod-detail description info static')
                        yield Label(f'{self.mod.get("server_side", "").title()}', classes='mod-detail description info label')

            with TabPane('Versions'):
                with Horizontal(classes='mod-detail versions'):
                    self.filter_sidebar = FilterSidebar(classes='mod-detail versions filter-sidebar')
                    yield self.filter_sidebar
                    self.version_list = VersionList(classes='mod-detail versions version-list focusable')
                    self.version_list.custom_loading = True
                    yield self.version_list

        

        yield Footer()

    async def on_mount(self):
        self.filter_sidebar.add_categories(['modloader', 'version', 'type'])

        self.get_mod_info()
        self.get_mod_versions()

    @work(thread=True)
    async def get_mod_info(self):
        # mod_info: published, updated
        self.mod_info = await self.source_api.get_mod(str(self.mod.get('project_id')))

        body = strip_images(self.mod_info.get('body', ''))
        self.call_later(self.update_markdown_label, self.description_label, body)

    @work(thread=True)
    async def get_mod_versions(self):
        # mod_versions: id, version_number, changelog, files[url, filename, primary]
        mod_versions = await self.source_api.get_mod_versions(str(self.mod.get('project_id')))

        modloaders = list({loader for version in mod_versions for loader in version.get('loaders', [])})

        release_versions = [v.get('id', '') for v in await get_minecraft_versions()]
        present_versions = list({mc_version for version in mod_versions for mc_version in version.get('game_versions', [])})
        mc_versions = [v for v in release_versions if v in present_versions]

        possible_types = ["release", "beta", "alpha"]
        types = [t for t in possible_types if any(v.get("version_type") == t for v in mod_versions)]

        self.mod_versions = [v for v in mod_versions for mc in mc_versions if mc in v.get('game_versions', [])]

        self.filter_sidebar.add_options('modloader', sorted(modloaders), [self.modloader])
        self.filter_sidebar.add_options('version', mc_versions, [self.mc_version])
        self.filter_sidebar.add_options('type', types)

        versions = [v for v in self.mod_versions if self.mc_version in v.get('game_versions', [])]

        self.call_later(self.version_list.set_versions, versions)

        self.call_later(lambda: setattr(self.version_list, 'custom_loading', False))

    def update_markdown_label(self, label: Label, text):
        label.update(Markdown(text))
        self.set_label_loading(label, False)

    def set_label_loading(self, label: Label, loading: bool):
        label.loading = loading
        label.styles.height = '1fr' if loading else 'auto'

    def action_back(self):
        self.dismiss()

    @on(VersionList.Selected)
    async def on_version_list_selected(self, event: VersionList.Selected) -> None:
        selected_version = event.item
