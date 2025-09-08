from typing import cast, get_args

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, VerticalGroup
from textual.events import Resize
from textual.widgets import Static, Label, Button

from screens.modals import FilterModal

from backend.api import get_minecraft_versions, ModrinthAPI, CurseforgeAPI

from helpers import SmartInput, CustomSelect, CustomTable, CustomModal, ModloaderType, FocusNavigationMixin

class ModBrowserModal(FocusNavigationMixin, CustomModal[str]):
    CSS_PATH = 'styles/modbrowser_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
            Binding('f', 'filter', 'Filter', show=True),
            Binding('r', 'reset', 'Reset', show=True),
        ] + FocusNavigationMixin.BINDINGS

    navigation_map = {
        "modbrowser-search":           {"left": "", "up": "", "down": "modbrowser-modloader-select", "right": "modbrowser-filter-button"},
        "modbrowser-filter-button":    {"left": "modbrowser-search", "up": "", "down": "modbrowser-mcversion-select", "right": "modbrowser-source-select"},
        "modbrowser-source-select":    {"left": "modbrowser-filter-button", "up": "", "down": "modbrowser-mcversion-select", "right": ""},
        "modbrowser-modloader-select": {"left": "", "up": "modbrowser-search", "down": "modbrowser-table", "right": "modbrowser-mcversion-select"},
        "modbrowser-mcversion-select": {"left": "modbrowser-modloader-select", "up": "modbrowser-filter-button", "down": "modbrowser-version-select", "right": ""},
        "modbrowser-table":            {"left": "", "up": "modbrowser-modloader-select", "down": "", "right": "modbrowser-version-select"},
        "modbrowser-version-select":   {"left": "modbrowser-table", "up": "modbrowser-mcversion-select", "down": "modbrowser-install-button", "right": ""},
        "modbrowser-install-button":   {"left": "modbrowser-table", "up": "modbrowser-version-select", "down": "", "right": ""},
    }

    sources = {
        "modrinth": {
            "api": ModrinthAPI(),
            "notify": None,
        },
        "curseforge": {
            "api": CurseforgeAPI(),
            "notify": "Curseforge support is not yet implemented.",
        },
    }

    def __init__(self, modloader: ModloaderType, mc_version: str, source: str = 'modrinth') -> None:
        super().__init__()
        self.modloader = modloader
        self.mc_version = mc_version
        self.source = source
        self.source_api = self.sources[self.source]['api']

    def compose(self) -> ComposeResult:
        self.grid = Grid(id='modbrowser-grid', classes='modbrowser grid')
        self.grid.border_title = 'Mod Browser'
        self.grid.border_subtitle = 'f to filter'
        with self.grid:
            with Grid(id='modbrowser-top-grid', classes='modbrowser grid top'):
                yield Static('Search:', classes='modbrowser text')
                self.input = SmartInput(placeholder='Search Mods...', id='modbrowser-search', classes='modbrowser input shrink')
                yield self.input
                yield Button('Filter', id='modbrowser-filter-button', classes='modbrowser button shrink')
                yield Static('Source:', classes='modbrowser text')
                self.source_select = CustomSelect([(key.capitalize(), key) for key in self.sources], allow_blank=False, id='modbrowser-source-select', classes='modbrowser select shrink')
                yield self.source_select

                yield Static('Modloader:', classes='modbrowser text')
                self.modloader_select = CustomSelect([(loader.capitalize(), loader) for loader in get_args(ModloaderType)], allow_blank=False, id='modbrowser-modloader-select', classes='modbrowser select shrink')
                yield self.modloader_select
                yield Static('MC Version:', id='modbrowser-mcversion-label', classes='modbrowser text')
                self.mcversion_select = CustomSelect([('...', '...')], allow_blank=False, disabled=True, id='modbrowser-mcversion-select', classes='modbrowser select shrink')
                yield self.mcversion_select

            self.list_group = VerticalGroup(classes='modbrowser group')
            self.list_group.border_title = 'Mods List'
            with self.list_group:
                self.mod_table = CustomTable(zebra_stripes=True, cursor_type='row', id='modbrowser-table', classes='modbrowser table')
                yield self.mod_table

            self.detail_grid = Grid(classes='modbrowser group detail')
            self.detail_grid.border_title = 'Details'
            with self.detail_grid:
                yield Static('Selected Mod:', classes='modbrowser text')
                self.selected_mod = Label('Select a Mod', id='modbrowser-selected-mod', classes='modbrowser text label')
                yield self.selected_mod

                yield Static('Version:', classes='modbrowser text')
                self.version_select = CustomSelect([('Select a Mod', 'Select a Mod')], allow_blank=False, id='modbrowser-version-select', classes='modbrowser select')
                yield self.version_select

                yield Static('Dependencies:', classes='modbrowser text wide')
                self.dependencies_grid = Grid(id='modbrowser-dependencies-grid', classes='modbrowser grid dependencies')
                yield self.dependencies_grid

                self.install_button = Button('Install', id='modbrowser-install-button', classes='modbrowser button shrink')
                yield self.install_button

            self.filter_label = Label(id='modbrowser-filter-label', classes='modbrowser text label hidden')

    async def on_mount(self):
        self.source_select.value = self.source
        self.modloader_select.value = self.modloader
        self.dependencies_grid.mount(Static('Select a Mod to see Dependencies', classes='modbrowser text wide'))
        self.mod_table.add_columns('Name', 'Author', 'Downloads', 'Loaders')
        await self.load_mods()
        # - ui still hangs while loading versions
        self.run_worker(self.load_mc_versions(), thread=True)

    async def load_mc_versions(self):
        mc_versions = await get_minecraft_versions()
        version_ids: list[tuple[str, str]] = [(v['id'], v['id']) for v in mc_versions]
        if version_ids:
            self.call_later(self.mcversion_select.set_options, version_ids)
            if self.mc_version in dict(version_ids):
                self.mcversion_select.value = self.mc_version
        self.mcversion_select.disabled = False

    @on(Resize)
    def on_resize(self, event: Resize):
        self.grid.styles.height = max(20, self.size.height * 0.9)
        self.grid.styles.width = max(81, self.size.width * 0.8)
        # - add dynamic button size to other buttons, screens and modals?
        if self.size.height * 0.9 < 25:
            # self.install_button.compact = True
            for widget in self.query('.shrink'):
                if isinstance(widget, (Button, SmartInput, CustomSelect)):
                    widget.compact = True
            self.query_one('#modbrowser-top-grid').styles.grid_rows = '1 1'
        else:
            # self.install_button.compact = False
            for widget in self.query('.shrink'):
                if isinstance(widget, (Button, SmartInput, CustomSelect)):
                    widget.compact = False
            self.query_one('#modbrowser-top-grid').styles.grid_rows = '3 3'


    async def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'back':
                self.action_back()
            case 'modbrowser-install-button':
                pass
            case 'modbrowser-filter-button':
                pass

    def action_back(self):
        self.dismiss()

    def action_focus_move(self, direction: str):
        focused = self.focused
        if not focused or not focused.id:
            return
        try:
            next_id = self.navigation_map.get(focused.id, {}).get(direction)
            if next_id:
                next_widget = self.query_one(f'#{next_id}')
                next_widget.focus()
        except Exception as e:
            self.notify(f"Failed to move focus. {e}", severity='error', timeout=5)

    @on(CustomSelect.Changed, '#modbrowser-source-select')
    def on_source_select_changed(self, event: CustomSelect.Changed) -> None:
        if event.value != self.source:
            self.source = str(event.value)
            self.source_api = self.sources[self.source]['api']
            notify = self.sources[self.source]['notify']
            if notify:
                self.notify(notify, severity='information', timeout=5)
            # - reload mods list

    @on(CustomSelect.Changed, '#modbrowser-modloader-select')
    def on_modloader_select_changed(self, event: CustomSelect.Changed) -> None:
        if event.value != self.modloader:
            self.modloader = cast(ModloaderType, str(event.value).lower())
            # - reload mods list

    @on(CustomSelect.Changed, '#modbrowser-mcversion-select')
    def on_mcversion_select_changed(self, event: CustomSelect.Changed) -> None:
        if event.value != self.mc_version:
            self.mc_version = str(event.value)
            # - reload mods list

    @on(CustomSelect.Changed, '#modbrowser-version-select')
    def on_version_select_changed(self, event: CustomSelect.Changed) -> None:
        pass

    async def load_mods(self):
        self.mod_table.loading = True
        self.mod_table.clear()
        # - get mods and display them in the datatable
        self.mod_table.loading = False

    async def load_dependencies(self):
        self.dependencies_grid.remove_children()
        # - get dependencies and mount them
