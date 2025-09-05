from shutil import rmtree
from typing import Literal, cast
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Grid, VerticalScroll
from textual.widgets import Button, Footer, Header, Static, Input, Select
from textual.screen import Screen
from textual.binding import Binding
from pathlib import Path
from datetime import datetime
from screens.selector_modal import SelectorModal
from screens.text_display_modal import TextDisplayModal
from screens.progress_modal import ProgressModal
from backend.api.api import SourceAPI
from backend.api.modrinth import ModrinthAPI
from backend.api.curseforge import CurseforgeAPI
from backend.api.ftb import FTBAPI
from backend.api.mojang import get_minecraft_versions
from backend.api.fabric import get_fabric_versions
from backend.api.forge import get_forge_versions
from backend.api.neoforge import get_neoforge_versions
from backend.api.quilt import get_quilt_versions
from backend.storage.instance import InstanceConfig
from helpers import format_date, sanitize_filename, CustomSelect, SmartInput

class NewInstanceScreen(Screen):
    CSS_PATH = 'styles/new_instance_screen.tcss'
    BINDINGS = [
        ('q', 'back', 'Back'),
        Binding('escape', 'back', show=False),
        ('i', 'install', 'Install'),
        Binding('up', "focus_move('up')", show=False),
        Binding('down', "focus_move('down')", show=False),
        Binding('left', "focus_move('left')", show=False),
        Binding('right', "focus_move('right')", show=False),
    ]

    navigation_map_modpack = {
        "source_select":        {"left":"",                     "up": "",                   "down": "project_input",        "right": "search_button"},
        "project_input":        {"left":"",                     "up": "source_select",      "down": "version_select",       "right": "search_button"},
        "search_button":        {"left":"project_input",        "up": "source_select",      "down": "modlist_button",       "right": "install"},
        "version_select":       {"left":"",                     "up": "project_input",      "down": "instance_name_input",  "right": "modlist_button"},
        "modlist_button":       {"left":"version_select",       "up": "search_button",      "down": "changelog_button",     "right": "install"},
        "instance_name_input":  {"left":"",                     "up": "version_select",     "down": "install",              "right": "changelog_button"},
        "changelog_button":     {"left":"instance_name_input",  "up": "modlist_button",     "down": "install",              "right": "install"},
        "install":              {"left":"changelog_button",     "up": "changelog_button",   "down": "",                     "right": "back"},
        "back":                 {"left":"install",              "up": "changelog_button",   "down": "",                     "right": ""},
    }

    navigation_map_modloader = {
        "source_select":                {"left":"",                             "up": "install",                    "down": "instance_name_input",          "right": "install"},
        "instance_name_input":          {"left":"",                             "up": "source_select",              "down": "mc_version_selector",          "right": "install"},
        "mc_version_selector":          {"left":"",                             "up": "instance_name_input",        "down": "modloader_selector",           "right": "install"},
        "modloader_selector":           {"left":"",                             "up": "mc_version_selector",        "down": "modloader_version_selector",   "right": "install"},
        "modloader_version_selector":   {"left":"",                             "up": "modloader_selector",         "down": "install",                      "right": "install"},
        "install":                      {"left":"modloader_version_selector",   "up": "modloader_version_selector", "down": "",                             "right": "back"},
        "back":                         {"left":"install",                      "up": "modloader_version_selector", "down": "",                             "right": ""},
    }

    sources = {
        "Modrinth": {
            "key": "modrinth",
            "api": ModrinthAPI(),
            "install_mode": "modpack",
            "notify": None,
        },
        "Curseforge": {
            "key": "curseforge",
            "api": CurseforgeAPI(),
            "install_mode": "modpack",
            "notify": "Curseforge support is not yet implemented.",
        },
        "FTB": {
            "key": "ftb",
            "api": FTBAPI(),
            "install_mode": "modpack",
            "notify": "FTB support is not yet implemented.",
        },
        "Modloader only": {
            "key": "modloader",
            "api": None,  # no API module here
            "install_mode": "modloader",
            "notify": None,
        },
    }

    _, default_source = next(iter(sources.items()))

    install_mode = default_source["install_mode"]

    source = default_source["key"]

    source_api: SourceAPI = default_source["api"]

    versions: list[dict] = []

    modpack_name: str = ''

    modpack_slug: str = ''

    selected_modpack_version: dict = {}

    modlist: list[dict] = []

    selected_minecraft_version: dict = {}

    selected_modloader: Literal["fabric", "forge", "neoforge", "quilt"]

    selected_modloader_version: str = ''

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Grid(id='new_instance_grid'):
            # Source selector
            yield Static('Source:', classes='text')
            yield CustomSelect.from_values(list(self.sources.keys()), allow_blank=False, id='source_select')

            yield Static(id='spacer1')
            
            # Project / Instance fields for Modpacks
            yield Static('Project:', classes='text modpack')
            self.search = SmartInput(placeholder='Search Modpack', id='project_input', classes='input modpack')
            yield self.search
            yield Button('Search', id='search_button', classes='button modpack')

            yield Static(id='spacer2', classes='modpack')

            yield Static('Version:', classes='text modpack')
            self.version_selector = Button('Select Version', id='version_select', classes='button modpack')
            yield self.version_selector
            yield Button('Modlist', id='modlist_button', classes='button modpack')

            yield Static(id='spacer3', classes='modpack')

            # Shared Fields
            yield Static('Instance Name:', classes='text')
            self.instance_name = SmartInput(placeholder='Instance Name', id='instance_name_input', classes='input')
            yield self.instance_name
            # Shared Fields end

            yield Button('View Changelog', id='changelog_button', classes='button modpack')

            yield Static(id='spacer4', classes='modpack')

            yield Static('Description:', id='description-label', classes='text modpack')
            self.description = Static(id='description_box', classes='text modpack', expand=True)
            yield VerticalScroll(self.description, id='description_scroll', classes='text modpack')

            yield Static('Author:', id='author-label', classes='text modpack')
            self.author = Static(id='author_box', classes='text modpack')
            yield self.author

            # Modloader-only fields
            yield Static(id='spacer5', classes='modloader')

            yield Static('Minecraft Version:', classes='text modloader')
            self.mc_version_selector = Button('Select Version', id='mc_version_selector', classes='button modloader') # replace with Select if release date doesn't matter
            yield self.mc_version_selector

            yield Static(id='spacer6', classes='modloader')

            yield Static('Modloader:', classes='text modloader')
            self.modloader_selector = CustomSelect.from_values(
                ["Fabric", "Forge", "NeoForge", "Quilt"],
                allow_blank=False, 
                id='modloader_selector', 
                classes='select modloader'
                )
            yield self.modloader_selector

            yield Static(id='spacer7', classes='modloader')

            yield Static('Modloader Version:', classes='text modloader')
            self.modloader_version_selector = Button('Select Version', id='modloader_version_selector', classes='button modloader') # replace with Select if not showing beta status
            yield self.modloader_version_selector

            yield Static(id='spacer8', classes='modloader')

            # Buttons
            with Horizontal(id='button-row'):
                yield Button('Install', id='install', classes='newinstance button')
                yield Button('Back', id='back', classes='newinstance button')

        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = 'New Instance'

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'back':
                self.action_back()
            case 'install':
                self.install()                    
            case 'search_button':
                self.search_modpack()
            case 'version_select':
                self.run_worker(self.select_version(), exclusive=True, name='version_select')
            case 'changelog_button':
                self.open_changelog()
            case 'mc_version_selector':
                self.run_worker(self.select_mc_version(), exclusive=True, name='mc_version_select')
            case 'modloader_version_selector':
                self.run_worker(self.select_modloader_version(), exclusive=True, name='modloader_version_select')
            case 'modlist_button':
                self.query_one('#modlist_button').loading = True
                self.run_worker(self.show_modlist(), exclusive=True, name='modlist_load')

    def on_input_submitted(self, event: Input.Submitted) -> None:
        match event.input.id:
            case 'project_input':
                self.search_modpack()
            case default:
                return

    async def open_modpack_selector(self, query: str):
        # - get limit from settings, add way to load more
        title, data = await self.source_api.search_modpacks(query, limit=20)

        if not title or not data:
            self.notify(f"Couldn't load Modpacks. Query: '{query}'", severity='error', timeout=5)
            return

        async def modpack_selected(result: str | None) -> None:
            if result:
                selected_pack = next((r for r in data if r["slug"] == result), None)
                if selected_pack: # ["Name", "Author", "Downloads", "Modloader", "Categories", "Slug", "Description"]
                    self.modlist = [] # clear modlist when changing modpack
                    self.modpack_name = str(selected_pack["name"])
                    self.modpack_slug = str(selected_pack["slug"])
                    self.instance_name.value = self.modpack_name
                    self.description.update(str(selected_pack["description"]))
                    self.author.update(str(selected_pack["author"]))
                    self.versions = await self.source_api.get_modpack_versions(str(selected_pack["slug"]))
                    if not self.versions:
                        self.notify(f"Couldn't get Modpack versions for {self.modpack_name}.", severity='error', timeout=5)
                    else:
                        self.version_selector.label = self.versions[0]["version_number"]
                        self.selected_modpack_version = self.versions[0]
            self.query_one('#search_button').loading = False


        await self.app.push_screen(
            SelectorModal(
                title=title,
                choices=data,
                return_field='slug',
                hide_return_field=True,
                filter_columns=["author", "modloader", "categories"]
            ),
            modpack_selected
        )

    def action_back(self):
        self.app.pop_screen()

    def action_install(self):
        self.install()

    def action_focus_move(self, direction: str):
        navigation_map = self.navigation_map_modpack if self.install_mode == 'modpack' else self.navigation_map_modloader
        focused = self.focused
        if not focused or not focused.id:
            return
        try:
            next_id = navigation_map.get(focused.id, {}).get(direction)
            if next_id:
                next_widget = self.query_one(f'#{next_id}')
                next_widget.focus()
        except Exception as e:
            self.notify(f"Failed to move focus. {e}", severity='error', timeout=5)

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        match event.select.id:
            case 'source_select':
                self.title = str(event.value)
                source = self.sources.get(str(event.value))

                if source:
                    self.set_install_mode(source["install_mode"])
                    self.source = source["key"]
                    self.source_api = source["api"]

                    # reset modpack selection
                    self.versions = []
                    self.modpack_name = ''
                    self.modpack_slug = ''
                    self.selected_modpack_version = {}
                    self.modlist = []
                    self.instance_name.value = ''
                    self.description.update('')
                    self.author.update('')
                    self.version_selector.label = 'Select Version'

                    if source["notify"]:
                        self.notify(source["notify"], severity='information', timeout=5)
            case 'modloader_selector':
                self.selected_modloader = cast(Literal["fabric", "forge", "neoforge", "quilt"], str(event.value).lower())

    def set_install_mode(self, mode: str):
        if mode == 'modpack':
            self.install_mode = 'modpack'
            # Hide modloader widgets, show modpack widgets
            for widget in self.query(".modloader"):
                widget.display = "none"

            for widget in self.query(".modpack"):
                widget.display = "block"
        else:
            self.install_mode = 'modloader'
            # Hide modpack widgets, show modloader widgets
            for widget in self.query(".modloader"):
                widget.display = "block"

            for widget in self.query(".modpack"):
                widget.display = "none"

    def install(self):
        def install_finished(result: str | None) -> None:
                self.query_one('#install').loading = False
                if result == 'finished':
                    self.dismiss(sanitize_filename(self.instance_name.value))
                else:
                    if instance.path.exists():
                        rmtree(instance.path)

        self.query_one('#install').loading = True

        instance_id = sanitize_filename(self.instance_name.value)
        instance_path = Path(f'instances/{instance_id}')

        # Check if instance exists, don't install if yes
        if (instance_path / 'instance.json').exists():
            self.notify(f"Instance '{instance_id}' already exists.", severity='error', timeout=5)
            self.query_one('#install').loading = False
            return
        
        # Clean up unfinished installation
        if instance_path.exists():
            rmtree(instance_path, ignore_errors=True)

        # Modpack install logic
        if self.install_mode == 'modpack':
            if not self.versions or not self.selected_modpack_version or not self.instance_name.value:
                self.notify('Could not install Modpack, make sure all Fields are filled.', severity="error", timeout=5)
                self.query_one('#install').loading = False
                return
            version = self.selected_modpack_version
            
            modpack_url = next((file["url"] for file in version["files"] if file.get("primary")), None)

            if version["loaders"][0] not in ("fabric", "forge", "neoforge", "quilt"):
                self.notify(f"Unsupported Modloader: {version["loaders"][0]}.", severity='error', timeout=5)
                self.query_one('#install').loading = False
                return

            instance = InstanceConfig(
                instance_id=instance_id,
                name=self.instance_name.value,
                install_date=datetime.now(),
                minecraft_version=version["game_versions"][0],
                modloader=version["loaders"][0],
                modpack_name=self.modpack_name,
                modpack_id=self.modpack_slug,
                modpack_url=modpack_url,
                modpack_version=version["version_number"],
                modpack_date=datetime.fromisoformat(version["date_published"]),
                modpack_source=self.source,
                path=instance_path,
            )

            self.app.push_screen(ProgressModal(instance, version["dependencies"], self.modlist, mode='modpack'), install_finished)

        # Modloader only install logic
        elif self.install_mode == 'modloader':
            if not self.selected_minecraft_version or not self.selected_modloader_version or not self.instance_name.value:
                self.notify('Could not install Modloader, make sure all Fields are filled.', severity="error", timeout=5)
                self.query_one('#install').loading = False
                return
            
            instance = InstanceConfig(
                instance_id=instance_id,
                name=self.instance_name.value,
                install_date=datetime.now(),
                minecraft_version=str(self.selected_minecraft_version), # ?
                modloader=self.selected_modloader,
                modloader_version=self.selected_modloader_version,
                path=instance_path,
            )

            self.app.push_screen(ProgressModal(instance, mode='modloader', mc_version_url=self.selected_minecraft_version["url"]), install_finished)

        else:
            self.notify(f"Unknown installation mode '{self.install_mode}'", severity='error', timeout=5)
            self.query_one('#install').loading = False

    def search_modpack(self):
        self.query_one('#search_button').loading = True
        self.run_worker(self.open_modpack_selector(self.search.value), exclusive=True, name='modpack_search')

    async def select_version(self):
        if not self.versions:
            self.notify('Please select a Modpack first.', severity='information', timeout=5)
            return

        self.version_selector.loading = True
        
        def version_chosen(result: str | None) -> None:
            if result:
                version = next((v for v in self.versions if v["id"] == result), None)
                if version:
                    self.version_selector.label = version["version_number"]
                    self.selected_modpack_version = version
                    self.modlist = [] # clear modlist when changing version
            self.version_selector.loading = False

        choices: list[dict[str, str | list[str]]] = [
            {
                "version": v["version_number"],
                "game_version": ", ".join(v.get("game_versions", [])),
                "modloader": ", ".join(v.get("loaders", [])).title(),
                "release_date": format_date(v["date_published"]),
                "version_type": v.get("version_type", "unknown").title(),
                "id": v["id"]
                if v.get("date_published") else ""
            }
            for v in self.versions
        ]
        if choices:
            self.app.push_screen(
                SelectorModal(
                    "Choose Modpack Version",
                    choices,
                    return_field='id',
                    hide_return_field=True,
                    filter_columns=['game_version', 'modloader', 'version_type']
                ),
                version_chosen
            )
        else:
            self.notify('Could not load Versions.', severity='error', timeout=5)

    def open_changelog(self):
        if not self.selected_modpack_version:
            self.notify('Please select a Modpack first.', severity='information', timeout=5)
            return
        changelog = self.selected_modpack_version['changelog']
        if changelog:
            self.app.push_screen(TextDisplayModal("Changelog", changelog))
        else:
            self.notify('Could not load Changelog.', severity='error', timeout=5)

    async def select_mc_version(self):
        self.mc_version_selector.loading = True
        
        def mc_version_chosen(result: str | None) -> None:
            if result:
                self.mc_version_selector.label = result
                self.selected_minecraft_version = next((version for version in mc_versions if version["id"] == result), {})
            self.mc_version_selector.loading = False
        mc_versions = await get_minecraft_versions()
        version_ids: list[dict[str, list[str] | str]] = []
        for version in mc_versions:
            formatted_date = format_date(version["releaseTime"])
            version_ids.append({"version": version["id"], "release_date": formatted_date})
        if version_ids:
            self.app.push_screen(
                SelectorModal(
                    "Choose Minecraft Version",
                    version_ids,
                    show_filter=False
                ),
                mc_version_chosen
            )
        else:
            self.notify('Could not load Minecraft Versions.', severity='error', timeout=5)
            self.mc_version_selector.loading = False

    async def select_modloader_version(self):
        if not self.selected_minecraft_version:
            self.notify("Please select Minecraft Version first.", severity='information', timeout=5)
            return
        self.modloader_version_selector.loading = True
        
        def modloader_version_chosen(result: str | None) -> None:
            if result:
                self.modloader_version_selector.label = result
                self.selected_modloader_version = result
            self.modloader_version_selector.loading = False
        versions_list: list[dict[str, list[str] | str]] = await self.get_modloader_versions(self.selected_minecraft_version["id"])
        filter_columns = {
            "fabric": ["stable"],
            "forge": [],
            "neoforge": [],
            "quilt": ["release"]
            }
        if versions_list:
            self.app.push_screen(
                SelectorModal(
                    "Choose Modloader Version",
                    versions_list,
                    filter_columns=filter_columns[self.selected_modloader],
                    show_filter=filter_columns[self.selected_modloader],
                    sort_column='version',
                    sort_reverse=True
                ),
                modloader_version_chosen
            )
        else:
            self.notify("Could not load Modloader Versions.", severity='error', timeout=5)
            self.modloader_version_selector.loading = False

    async def get_modloader_versions(self, mc_version) -> list[dict[str, list[str] | str]]:
        match self.selected_modloader:
            case 'fabric':
                versions = await get_fabric_versions(mc_version)
                return [{"version": v["version"], "stable": str(v["stable"])} for v in versions]
            case 'forge':
                # - sorting is ascending, should be descending
                versions = await get_forge_versions(mc_version)
                return [{"version": v["forge_version"]} for v in versions]
            case 'neoforge':
                versions = await get_neoforge_versions(mc_version)
                return [{"version": v["full_version"]} for v in versions]
            case 'quilt':
                versions = await get_quilt_versions(mc_version)
                return [{"version": v["version"], "release": str(v["release"])} for v in versions]

    async def show_modlist(self):
        if not self.selected_modpack_version:
            self.notify('Please select a Modpack first.', severity='information', timeout=5)
            return
        if self.modlist:
            modlist = self.modlist
        else:
            modlist = await self.source_api.get_modlist(self.selected_modpack_version["dependencies"])
        if modlist:
            self.modlist = modlist
            formatted_modlist = "\n".join(f"- {mod['name']} ({mod['version_number']})" for mod in sorted(modlist, key=lambda m: m['name'].lower()))
            self.app.push_screen(TextDisplayModal("Modlist", formatted_modlist))
        else:
            self.notify('Could not load Modlist.', severity='error', timeout=5)
        self.query_one('#modlist_button').loading = False

