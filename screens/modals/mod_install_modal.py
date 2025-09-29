from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, HorizontalGroup
from textual.widgets import Button, Label, Checkbox

from backend.api import SourceAPI, ModrinthAPI, CurseforgeAPI
from backend.storage import InstanceConfig

from helpers import CustomModal, CustomVerticalScroll

class ModInstallModal(CustomModal[bool]):
    """Modal for installing mods. Returns `True` if install successful, `False` otherwise."""
    CSS_PATH = 'styles/mod_install_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'back', show=False),
        ]

    def __init__(self, mod: dict, mod_name: str, instance: InstanceConfig, source: str, source_api: SourceAPI):
        super().__init__()
        self.mod = mod
        self.dependencies = mod.get('dependencies', [])
        self.instance = instance
        self.modloader = instance.modloader
        self.mc_version = instance.minecraft_version
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
        self.get_dependencies()
        # - first get dependencies
        # - mount dependencies to self.dependency_scroll

    @work(thread=True)
    async def get_dependencies(self):
        project_ids = [dep.get('project_id', '') for dep in self.dependencies]
        version_ids = [dep.get('version_id', '') for dep in self.dependencies]

        dependencies = []
        for dep in self.dependencies:
            dependencies.append(await self.source_api.get_dependency(dep.get('project_id', ''), dep.get('version_id', ''), self.modloader, self.mc_version))
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
