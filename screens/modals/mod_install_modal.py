from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, HorizontalGroup
from textual.widgets import Button, Label, Checkbox

from backend.api import SourceAPI, ModrinthAPI, CurseforgeAPI
from backend.storage import InstanceConfig

from helpers import NavigationMixin, CustomModal, CustomVerticalScroll

class ModInstallModal(NavigationMixin, CustomModal[bool]):
    """Modal for installing mods. Returns `True` if install successful, `False` otherwise."""
    CSS_PATH = 'styles/mod_install_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
        ] + NavigationMixin.BINDINGS

    def __init__(self, mod: dict, mod_name: str, instance: InstanceConfig, source: str, source_api: SourceAPI):
        super().__init__()
        self.mod = mod
        self.dependencies = mod.get('dependencies', [])
        self.instance = instance
        self.modloader = mod.get('loaders', [instance.modloader])
        self.mc_version = mod.get('game_versions', [instance.minecraft_version])
        self.source = source
        self.source_api = source_api
        self.border_title = 'Select dependencies to install:'
        self.border_sub_title = f'{mod_name} ({mod.get('version_number', 'Unknown Version')})'

    def compose(self) -> ComposeResult:
        with Vertical(classes='mod-install main-container'):
            self.dependency_scroll = CustomVerticalScroll(classes='mod-install dependencies')
            yield self.dependency_scroll

            with HorizontalGroup(classes='mod-install buttons'):
                yield Button('Back', id='mod-install-back-button', classes='mod-install button focusable')
                yield Button('Install', id='mod-install-install-button', classes='mod-install button focusable')

    def on_mount(self) -> None:
        self.dependency_scroll.loading = True
        self.get_dependencies()

    @work(thread=True)
    async def get_dependencies(self):
        dependencies = await self.source_api.get_modlist(self.dependencies, self.mc_version, self.modloader)
        for dep in dependencies:
            dep['dependency_type'] = [dependency.get('dependency_type', 'unknown') for dependency in self.dependencies if dependency.get('project_id') == dep.get('project_id')][0]
            dep['installed'] = True if self.instance.mods.get_mod(dep.get('project_id', '')) else False
            dep['force_install'] = True if dep.get('dependency_type', '') == 'required' else False
            dep['client_only'] = True if dep.get('server_side', '') == 'unsupported' else False

        # - add check if dependency already installed
        # - mount dependencies to self.dependency_scroll
        # dependencies: project_id, version_id, slug, name, description, version_number, date_published, file_name, download_url, loaders, type, server_side, client_side, dependency_type

        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'mod-install-back-button':
                self.action_back()
            case 'mod-install-install-button':
                self.install_mod()

    def action_back(self):
        self.dismiss(False)

    def install_mod(self):
        ...
