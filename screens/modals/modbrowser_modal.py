from typing import cast, get_args

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, VerticalGroup, VerticalScroll
from textual.events import Resize
from textual.widgets import Static, Label, Button, Checkbox

from screens.modals import FilterModal

from backend.api import get_minecraft_versions, ModrinthAPI, CurseforgeAPI
from backend.api.api import SourceAPI

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
            "mod_identifier": "slug",
        },
        "curseforge": {
            "api": CurseforgeAPI(),
            "notify": "Curseforge support is not yet implemented.",
            "mod_identifier": "project_id",
        },
    }

    mods: list[dict] = []

    selected_mod: dict = {}

    mod_versions: list[dict] = []

    selected_mod_version: dict = {}

    dependencies: list[dict] = []

    dependencies_info: dict = {}

    selected_dependencies: dict[str, bool] = {}

    filters: dict = {}

    COLUMNS = ['Name', 'Author', 'Downloads', 'Type', 'Loaders']

    def __init__(self, modloader: ModloaderType, mc_version: str, source: str = 'modrinth') -> None:
        super().__init__()
        self.modloader = modloader
        self.mc_version = mc_version
        self.source = source
        self.source_api: SourceAPI = self.sources[self.source]['api']

    def compose(self) -> ComposeResult:
        # main grid
        self.grid = Grid(id='modbrowser-grid', classes='modbrowser grid')
        self.grid.border_title = 'Mod Browser'
        self.grid.border_subtitle = 'f to filter'
        with self.grid:
            # top toolbar grid
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

            # mod list
            self.list_group = VerticalGroup(classes='modbrowser group')
            self.list_group.border_title = 'Mods List'
            with self.list_group:
                self.mod_table = CustomTable(zebra_stripes=True, cursor_type='row', id='modbrowser-table', classes='modbrowser table')
                yield self.mod_table

            # mod details grid
            self.detail_grid = Grid(classes='modbrowser group detail')
            self.detail_grid.border_title = 'Details'
            with self.detail_grid:
                yield Static('Selected Mod:', classes='modbrowser text')
                self.selected_mod_label = Label('Loading...', id='modbrowser-selected-mod', classes='modbrowser text label')
                yield self.selected_mod_label

                yield Static('Version:', classes='modbrowser text')
                self.version_select = CustomSelect([('Loading...', 'Loading...')], allow_blank=False, disabled=True, id='modbrowser-version-select', classes='modbrowser select shrink')
                yield self.version_select

                yield Static('Description:', id='modbrowser-description-label', classes='modbrowser text')
                self.description = Static(id='modbrowser-description', classes='modbrowser text description', expand=True)
                yield VerticalScroll(self.description, id='modbrowser-description-scroll', classes='modbrowser description-scroll')

                # dependencies grid
                yield Static('Dependencies:', classes='modbrowser text wide')
                self.dependencies_grid = Grid(id='modbrowser-dependencies-grid', classes='modbrowser grid dependencies')
                yield VerticalScroll(self.dependencies_grid, id='modbrowser-dependencies-scroll', classes='modbrowser dependencies-scroll')

                self.install_button = Button('Install', id='modbrowser-install-button', classes='modbrowser button shrink')
                yield self.install_button

            self.filter_label = Label(id='modbrowser-filter-label', classes='modbrowser text label hidden')
            yield self.filter_label

    async def on_mount(self):
        self.source_select.value = self.source
        self.modloader_select.value = self.modloader
        self.mod_table.add_columns(*self.COLUMNS)
        self.search_mods()
        self.run_worker(self.load_mc_versions(), thread=True)

    async def load_mc_versions(self):
        """Get Minecraft versions and load into mcversion_select."""
        mc_versions = await get_minecraft_versions()
        version_ids: list[tuple[str, str]] = [(v['id'], v['id']) for v in mc_versions]
        if version_ids:
            self.call_later(self.mcversion_select.set_options, version_ids)
            if self.mc_version in dict(version_ids):
                self.call_later(self.mcversion_select.set_value, self.mc_version)
        self.mcversion_select.disabled = False

    @on(Resize)
    def on_resize(self, event: Resize):
        self.grid.styles.height = max(20, self.size.height * 0.9)
        self.grid.styles.width = max(81, self.size.width * 0.8)
        self.query_one('#modbrowser-description-scroll').styles.max_height = f'{self.size.height * 0.15}'

        # - add dynamic button size to other buttons, screens and modals?
        compact_mode = self.size.height * 0.9 < 25
        for widget in self.query('.shrink'):
            if isinstance(widget, (Button, SmartInput, CustomSelect)):
                widget.compact = compact_mode
        
        self.query_one('#modbrowser-top-grid').styles.grid_rows = '1 1' if compact_mode else '3 3'

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'back':
                self.action_back()
            case 'modbrowser-install-button':
                pass
            case 'modbrowser-filter-button':
                self.action_filter()

    @on(Checkbox.Changed)
    def on_dependency_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id and event.checkbox.id.startswith('dep-check-'):
            project_id = event.checkbox.id.removeprefix('dep-check-')
            if project_id:
                self.selected_dependencies[project_id] = event.value

    def action_back(self):
        self.dismiss()

    @on(CustomSelect.Changed, '#modbrowser-source-select')
    def on_source_select_changed(self, event: CustomSelect.Changed) -> None:
        if event.value != self.source:
            self.source = str(event.value)
            self.source_api = self.sources[self.source]['api']
            notify = self.sources[self.source]['notify']
            if notify:
                self.notify(notify, severity='information', timeout=5)
            self.search_mods()

    @on(CustomSelect.Changed, '#modbrowser-modloader-select')
    def on_modloader_select_changed(self, event: CustomSelect.Changed) -> None:
        if event.value != self.modloader:
            self.modloader = cast(ModloaderType, str(event.value).lower())
            self.search_mods()

    @on(CustomSelect.Changed, '#modbrowser-mcversion-select')
    def on_mcversion_select_changed(self, event: CustomSelect.Changed) -> None:
        if event.value != self.mc_version and event.value != '...':
            self.mc_version = str(event.value)
            self.search_mods()

    @on(CustomSelect.Changed, '#modbrowser-version-select')
    def on_version_select_changed(self, event: CustomSelect.Changed) -> None:
        selected_version_number = str(event.value)
        new_selected_version = next((v for v in self.mod_versions if v.get('version_number') == selected_version_number), None)
        if new_selected_version and new_selected_version.get('id') != self.selected_mod_version.get('id'):
            self.selected_mod_version = new_selected_version
            self.dependencies = self.selected_mod_version.get('dependencies', [])
            self.run_worker(self.load_dependencies())

    @on(CustomTable.RowSelected)
    async def on_data_table_row_selected(self, event: CustomTable.RowSelected) -> None:
        new_row = event.row_key.value
        if new_row == self.selected_mod.get('slug'):
            return
        selected_row = str(event.row_key.value) or 'Select a Mod'
        self.version_select.set_options([('Loading...', 'Loading...')])
        self.version_select.disabled = True
        self.dependencies_grid.remove_children()
        self.dependencies_grid.mount(Static('Loading Dependencies...', classes='modbrowser text wide'))
        await self.load_versions(selected_row)

    @on(SmartInput.Submitted)
    def on_input_submitted(self, event: SmartInput.Submitted) -> None:
        match event.input.id:
            case 'modbrowser-search':
                self.search_mods()
            case default:
                return

    @work(thread=True)
    async def search_mods(self):
        """Search mods on the selected source."""
        query = self.input.value
        filters = {
            'modloader': [self.modloader],
            'mc_version': [self.mc_version],
        }
        filters.update(self.filters)

        data = await self.source_api.search_mods(query, filters=filters)
        self.mod_table.clear()
        if data:
            self.call_later(self.load_mods, data)
        else:
            self.notify(f"Couldn't load Mods. Query: '{query}'", severity='error', timeout=5)

    @work(thread=True)
    async def get_mod_versions(self, project_id: str):
        """Get versions for selected mod."""
        self.mod_versions = await self.source_api.get_mod_versions(project_id, self.mc_version, self.modloader)
        if not self.mod_versions:
            self.call_later(self.version_select.set_options, [('No versions found', '')])
            self.dependencies = []
            self.run_worker(self.load_dependencies())
            return

        version_numbers = [(version.get('version_number', ''), version.get('version_number', '')) for version in self.mod_versions]
        self.selected_mod_version = self.mod_versions[0]
        self.dependencies = self.selected_mod_version.get('dependencies', [])
        self.call_later(self.version_select.set_options, version_numbers)
        self.version_select.disabled = False
        self.run_worker(self.load_dependencies())

    async def load_mods(self, data: list[dict] | None = None):
        """Load mods into the table."""
        self.mod_table.loading = True
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
                    # - curseforge support? duplicate project id in poject_id and slug for curseforge?
                    key=mod.get('slug')
                )
        else:
            self.mod_table.add_row("No results found", key="")
        self.mod_table.loading = False

        selected_row = next(iter(self.mod_table.rows.keys())).value
        await self.load_versions(selected_row)

    async def load_versions(self, mod_id: str | None):
        """Load versions for selected mod."""
        if not mod_id:
            return
        identifier = self.sources[self.source]['mod_identifier']
        self.selected_mod = [mod for mod in self.mods if mod.get(identifier, '') == mod_id][0]
        self.selected_mod_label.update(self.selected_mod.get('name', ''))
        self.description.update(self.selected_mod.get('description', 'Not Available'))
        self.get_mod_versions(self.selected_mod.get(identifier))

    async def load_dependencies(self):
        """"Load dependencies for selected version."""
        self.dependencies_grid.remove_children()
        self.dependencies_grid.mount(Static('Loading Dependencies...', classes='modbrowser text wide'))

        self.dependencies_info = {}
        self.selected_dependencies = {}

        if not self.dependencies:
            self.dependencies_grid.remove_children()
            self.dependencies_grid.mount(Static('No dependencies for this version.', classes='modbrowser text wide'))
            return

        project_ids = [dep['project_id'] for dep in self.dependencies if dep.get('project_id')]
        if not project_ids:
            self.dependencies_grid.remove_children()
            self.dependencies_grid.mount(Static('No dependencies with project IDs found.', classes='modbrowser text wide'))
            return

        self.dependencies_info = await self.source_api.fetch_projects(project_ids, filter_server_side=False)

        await self.dependencies_grid.remove_children()

        if not self.dependencies_info and self.source == 'modrinth' and project_ids:
            self.dependencies_grid.mount(Static('Could not fetch dependency info. Some may be client-side only.', classes='modbrowser text wide'))
            return

        for dep in self.dependencies:
            project_id = dep.get('project_id', '')
            project_info = self.dependencies_info.get(project_id)

            is_required = dep.get('dependency_type') == 'required'
            checkbox = Checkbox('', value=is_required, compact=True, id=f"dep-check-{project_id}", classes='modbrowser checkbox')

            # - dependency selection only on pressing "install" -> modal; in details just include dependencies as text
            # - save dependencies to more easily install them afterwards
            
            # - navigation map doesn't work right, for now disabled
            # self.navigation_map[str(checkbox.id)] = {"left": "modbrowser-table", "right": ""}
            # self.navigation_map[str(checkbox.id)]["up"] = "modbrowser-version-select" if len(self.dependencies_grid.children) == 0 else str(self.dependencies_grid.children[-2].id)
            # self.navigation_map[str(checkbox.id)]["down"] = "modbrowser-install-button"
            
            # # Update previous checkbox's down navigation
            # if len(self.dependencies_grid.children) > 0:
            #     prev_checkbox_id = self.dependencies_grid.children[-2].id
            #     self.navigation_map[str(prev_checkbox_id)]["down"] = str(checkbox.id)

            if not project_info:
                # The project ID from the dependency list was not found by the API.
                dep_name = f"{project_id or 'Unknown'} [yellow](Not Found)[/yellow]"
                checkbox.value = False
                checkbox.disabled = True
            else:
                dep_name = project_info.get('title', project_id)
                # If a dependency is client-side only, disable its checkbox and indicate it.
                if project_info.get('server_side') == 'unsupported':
                    checkbox.value = False
                    checkbox.disabled = True
                    dep_name += ' [red](Client-side)[/red]'

            dep_type = dep.get('dependency_type', 'unknown')
            if project_id:
                self.selected_dependencies[project_id] = checkbox.value

            dep_type_styled = f"({dep_type})"
            match dep_type:
                case 'required':
                    dep_type_styled = f"([green]{dep_type}[/green])"
                case 'optional':
                    dep_type_styled = f"([yellow]{dep_type}[/yellow])"
                case 'incompatible':
                    dep_type_styled = f"([red]{dep_type}[/red])"
                    checkbox.value = False
                    checkbox.disabled = True
                case default:
                    dep_type_styled = f"({dep_type})"

            label = Label(f"{dep_name} {dep_type_styled}")

            self.dependencies_grid.mount(checkbox, label)

    def action_filter(self):
        """Open the filter modal."""
        def filter_chosen(filter: dict | None) -> None:
            if filter:
                formatted_filters = ' | '.join(
                    f"{col.title()}: {', '.join(val) if isinstance(val, list) else val.strip('[]').replace('\'','')}" 
                    for col, val in filter.items()
                )
                self.filter_label.update(f'Filter: {formatted_filters}')
                self.filter_label.remove_class('hidden')
                self.filters = filter
            else:
                self.filter_label.update('')
                self.filter_label.add_class('hidden')
                self.filters = {}
            self.search_mods()
        
        self.app.push_screen(FilterModal([{'type': 'Mod'}, {'type': 'Datapack'}], ['type']), filter_chosen)

# - imma be honest, i need way better selection and filtering logic, this ain't working
# - some mods support multiple loaders, by default it should be for the instance modloader
# - but especially with datapacks you need the ability to select if you want the datapack version or mod version of it
# - (often available as datapack, forge-, fabric-, neoforge- and quilt-mod)
