import asyncio
from typing import get_args

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import  VerticalGroup, HorizontalGroup
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button

from backend.api import get_minecraft_versions, ModrinthAPI, CurseforgeAPI
from backend.api.api import SourceAPI
from backend.storage import InstanceConfig

from helpers import SmartInput, CustomSelect, CustomTable, ModloaderType, FocusNavigationMixin, FilterSidebar, ModCard, ModList

class ModBrowserScreen(FocusNavigationMixin, Screen):
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

    # - switch to dict keyed by slug for fast lookups
    mods: list[dict] = []

    selected_mod: dict = {}

    COLUMNS = ['Name', 'Author', 'Downloads', 'Type', 'Loaders', 'Categories']

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
            self.list_group = VerticalGroup(classes='modbrowser modlist group')
            self.list_group.border_title = 'Mods List'
            with self.list_group:
                self.mod_table = CustomTable(zebra_stripes=True, cursor_type='row', id='modbrowser-table', classes='modbrowser table focusable')
                yield self.mod_table
            self.modlist = ModList(id='modbrowser-modlist', classes='modbrowser modlist focusable')
            yield self.modlist

            yield Footer()

    async def on_mount(self):
        self.sub_title = self.instance.name + ' - ModBrowser'

        self.source_select.value = self.source

        self.mod_table.add_columns(*self.COLUMNS)
        self.search_mods(first_load=True)

        self.filter_sidebar.add_categories(['modloader', 'version', 'category'])

        self.get_filter_options()

    @work(thread=True)
    async def get_filter_options(self):
        """Get options for the filter sidebar and populate it."""
        modloaders = [loader for loader in get_args(ModloaderType)]
        self.call_later(self.filter_sidebar.add_options, 'modloader', modloaders, [self.modloader])

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

    @on(CustomTable.RowSelected)
    async def on_data_table_row_selected(self, event: CustomTable.RowSelected) -> None:
        new_row = event.row_key.value
        if new_row == self.selected_mod.get('slug'):
            return
        selected_row = str(event.row_key.value)
        # - open details screen for mod

    @on(SmartInput.Submitted, '#modbrowser-search')
    def on_input_submitted(self, event: SmartInput.Submitted) -> None:
        self.search_mods()

    @work(thread=True)
    async def search_mods(self, first_load: bool = False):
        """Search mods on the selected source."""
        self.call_later(lambda: setattr(self.mod_table, 'loading', True))
        query = self.input.value
        if first_load:
            filters = {
                'modloader': [self.modloader],
                'version': [self.mc_version],
            }
        else:
            filters = self.filter_sidebar.get_selected_filters()

        data = await self.source_api.search_mods(query, filters=filters)
        self.mod_table.clear()
        if data:
            self.call_later(self.load_mods, data)
        else:
            self.notify(f"Couldn't load Mods. Query: '{query}'", severity='error', timeout=5)

    async def load_mods(self, data: list[dict] | None = None):
        """Load mods into the table."""
        # self.mod_table.loading = True
        self.mod_table.clear(columns=True)
        self.mod_table.add_columns(*self.COLUMNS)
        if data:
            self.mods = data
            for mod in data:
                self.mod_table.add_row(
                    mod.get('name', ''),
                    mod.get('author', ''),
                    mod.get('downloads', ''),
                    ', '.join(mod.get('type', '')).title(),
                    ', '.join(mod.get('modloader', [])),
                    ', '.join(mod.get('categories', [])),
                    # - curseforge support? duplicate project id in poject_id and slug for curseforge?
                    key=mod.get('slug')
                )
        else:
            self.mod_table.add_row("No results found")
        self.mod_table.loading = False
        self.modlist.set_mods(self.mods)

    @on(ModCard.Selected)
    def on_mod_card_selected(self, event: ModCard.Selected) -> None:
        selected_mod = event.mod
        # - open mod detail screen and pass selected_mod to it

# - make custom modlist table using widgets
# - inspired by modrinth modbrowser

