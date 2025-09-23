import asyncio
from typing import get_args

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import  VerticalGroup, HorizontalGroup
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Header, Footer, Static, Button

from backend.api import get_minecraft_versions, SourceAPI, ModrinthAPI, CurseforgeAPI
from backend.storage import InstanceConfig

from screens import ModDetailScreen

from helpers import SmartInput, CustomSelect, ModloaderType, FocusNavigationMixin, DebounceMixin
from widgets import FilterSidebar, ModList

class ModBrowserScreen(FocusNavigationMixin, DebounceMixin, Screen):
    CSS_PATH = 'styles/modbrowser_screen.tcss'
    BINDINGS = [
        Binding('q', "back", "Back", show=True),
        Binding('escape', "back", "Back", show=False),
        Binding('r', 'reset', 'Reset', show=True),
    ] + FocusNavigationMixin.BINDINGS

    sources = {
        "modrinth": {
            "api": ModrinthAPI(),
            "notify": None,
        },
        "curseforge": {
            "api": CurseforgeAPI(),
            # - remove once it's implemented
            "notify": "Curseforge support is not yet implemented.",
        },
    }

    mods: list[dict] = []

    selected_mod: dict = {}

    def __init__(self, instance: InstanceConfig) -> None:
        super().__init__()
        self.instance: InstanceConfig = instance
        self.modloader = instance.modloader
        self.mc_version = instance.minecraft_version
        self.source = instance.source_api
        self.source_api: SourceAPI = self.sources[self.source]['api']

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        # main group
        with VerticalGroup(id='modbrowser-group', classes='modbrowser main group'):
            # filter sidebar
            self.filter_sidebar = FilterSidebar(id='modbrowser-filter-sidebar', classes='modbrowser filter-sidebar')
            yield self.filter_sidebar

            # top toolbar
            with HorizontalGroup(id='modbrowser-top-bar', classes='modbrowser top-bar'):
                self.input = SmartInput(placeholder='Search Mods...', id='modbrowser-search', classes='modbrowser input focusable')
                yield self.input
                yield Static('Source:', id='modbrowser-source-label' ,classes='modbrowser text')
                self.source_select = CustomSelect([(key.capitalize(), key) for key in self.sources], allow_blank=False, id='modbrowser-source-select', classes='modbrowser select focusable')
                yield self.source_select
                yield Button('Back', id='modbrowser-back-button', classes='focusable modbrowser button')

            # mod list
            self.modlist = ModList(id='modbrowser-modlist', classes='modbrowser modlist focusable')
            yield self.modlist

        yield Footer()

    async def on_mount(self):
        self.sub_title = self.instance.name + ' > ModBrowser'

        self.source_select.value = self.source

        self.input.focus()

        self.search_mods(first_load=True)

        self.filter_sidebar.add_categories(['modloader', 'version', 'type', 'category'])

        self.get_filter_options()

    @work(thread=True)
    async def get_filter_options(self):
        """Get options for the filter sidebar and populate it."""
        modloaders = [loader for loader in get_args(ModloaderType)]
        self.call_later(self.filter_sidebar.add_options, 'modloader', modloaders, [self.modloader])

        types = ['mod', 'datapack']
        self.call_later(self.filter_sidebar.add_options, 'type', types, types)

        mc_versions, categories = await asyncio.gather(get_minecraft_versions(), self.source_api.get_categories())
        
        version_ids: list[str] = [v['id'] for v in mc_versions]
        if version_ids:
            self.call_later(self.filter_sidebar.add_options, 'version', version_ids, [self.mc_version])
        
        if categories:
            self.call_later(self.filter_sidebar.add_options, 'category', categories)

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'modbrowser-back-button':
                self.action_back()

    def action_back(self):
        self.dismiss()

    def action_reset(self):
        self.filter_sidebar.reset_filters()
        self.search_mods()

    @on(CustomSelect.Changed, '#modbrowser-source-select')
    def on_source_select_changed(self, event: CustomSelect.Changed) -> None:
        if event.value != self.source:
            self.source = str(event.value)
            self.source_api = self.sources[self.source]['api']
            notify = self.sources[self.source]['notify']
            if notify:
                self.notify(notify, severity='information', timeout=5)
            self.search_mods()

    @on(SmartInput.Changed, '#modbrowser-search')
    def on_input_changed(self, event: SmartInput.Changed) -> None:
        self.debounce('search', 0.5, self.search_mods)

    @work(thread=True)
    async def search_mods(self, first_load: bool = False):
        """Search mods on the selected source."""
        self.call_later(lambda: setattr(self.modlist, 'custom_loading', True))
        query = self.input.value
        if first_load:
            filters = {
                'modloader': [self.modloader],
                'version': [self.mc_version],
            }
        else:
            filters = self.filter_sidebar.get_selected_filters()

        data = await self.source_api.search_mods(query, filters=filters)
        if data:
            self.call_later(self.modlist.set_mods, data)
        else:
            self.notify(f"Couldn't load Mods. Query: '{query}'", severity='error', timeout=5)

    @on(FilterSidebar.FilterChanged)
    def on_filter_sidebar_filter_changed(self, event: FilterSidebar.FilterChanged) -> None:
        self.debounce('search', 0.5, self.search_mods)

    @on(ModList.Selected)
    async def on_mod_list_selected(self, event: ModList.Selected) -> None:
        selected_mod = event.item
        self.app.push_screen(ModDetailScreen(selected_mod, self.source, self.sub_title or '', self.instance))

