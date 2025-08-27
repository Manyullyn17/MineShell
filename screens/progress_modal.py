import asyncio
from pathlib import Path
from aioshutil import rmtree
from textual import work
from textual.widgets import Label, Static, Button, ProgressBar
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.containers import Grid, Container, HorizontalGroup
from backend.api.mojang import get_minecraft_versions
from backend.storage.instance import InstanceConfig, InstanceRegistry
from backend.installer.installer import install_modpack, install_modloader
from screens.delete_modal import DeleteModal

class ProgressModal(ModalScreen):
    CSS_PATH = 'styles/progress_modal.tcss'
    BINDINGS = [
            Binding('q', 'cancel', show=False),
            Binding('escape', 'cancel', show=False),
        ]

    def __init__(self, instance: InstanceConfig, dependencies: list[dict] | None = None, modlist: list[dict] | None = None, mode: str = 'modpack', mc_version_url: str | None = None) -> None:
        super().__init__()
        self.instance = instance
        self.steps = [
            '1. Downloading Modpack',
            '2. Extracting Modpack',
            f'3. Installing {instance.formatted_modloader()} Modloader',
            '4. Copying Overrides',
            '5. Getting Modlist',
            '6. Downloading Mods',
            '7. Finalizing Installation'
        ]
        self.modloader_steps = [
            '1. Getting Modloader installer',
            '2. Installing Modloader',
            '3. Finalizing Installation'
        ]
        self.dependencies = dependencies
        self.modlist = modlist
        self.mode = mode
        self.mc_version_url = mc_version_url

    def compose(self) -> ComposeResult:
        self.progress_step = Label(id="progress-step", classes='progress label')
        self.progress_bar = ProgressBar(id='progress-bar', classes='progress bar')
        self.progress_substep = Label(id="progress-substep", classes='progress label')
        self.sub_progress_bar = ProgressBar(id='sub-progress-bar', show_eta=False, classes='progress bar')
        yield Grid(
            Static(f"Creating Instance - {self.instance.name}", id='progress-title', classes='progress static'),
            self.progress_step,
            self.progress_bar,
            self.progress_substep,
            self.sub_progress_bar,
            HorizontalGroup(
                Button("Cancel", variant='error', id="cancel-install", classes='progress button'), 
                Button("Retry", variant='primary', id="retry-install", classes='progress button'), 
                id='progress-cancel-container'),
            Container(Button("Finish", variant='success', id="finish", classes='progress button'), id='progress-finish-container'),
            id='progress-dialog'
        )

    def on_mount(self) -> None:
        self.cancel_event = asyncio.Event()
        self.start_install()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "cancel-install":
                # cancel logic
                self.cancel_event.set()
                self.query_one('#cancel-install').disabled = True
                self.progress_step.update('Cancelling installation...')
            case "finish":
                self.dismiss('finished')
            case "retry": # doesn't work? it should though
                self.query_one('#retry-install').disabled = True
                self.start_install()

    @work(thread=True)
    async def start_install(self):
        try:
            if self.mode == 'modpack' and self.dependencies:
                dependencies = [
                    {"project_id": dep["project_id"], "version_id": dep["version_id"]}
                    for dep in self.dependencies
                    if dep.get("project_id") and dep.get("version_id")
                ]
                if self.instance.modloader in ['forge', 'neoforge']:
                    self.mc_version_url = [version["url"] for version in get_minecraft_versions() if version["id"] == self.instance.minecraft_version][0]
                status, message = await install_modpack(self.instance, self.steps, dependencies, self.progress_bar_callback, self.step_callback, self.cancel_event, self.modlist, self.mc_version_url)
            elif self.mode == 'modloader':
                status, message = await install_modloader(self.instance, self.modloader_steps, self.progress_bar_callback, self.step_callback, self.cancel_event, self.mc_version_url)
            else:
                return

            if status == 0:
                self.notify(f'Instance {self.instance.name} succesfully created!', severity='information', timeout=5)
                self.update_instances()
                self.set_finished()
                return
            elif status == -1:
                self.notify('Installation cancelled', severity='information', timeout=5)
                self.app.call_from_thread(self.dismiss, 'cancelled')

            self.notify(f'Installation failed on step {status}: {message}', severity='error', timeout=5)
            instance_path = Path('instances') / self.instance.instance_id
            if instance_path.exists():
                await rmtree(instance_path, ignore_errors=True)
            self.query_one('#retry-install').disabled = False
            self.query_one('#retry-install').display = 'block'
        except Exception as e:
            self.notify(f'Installation failed: {e}', severity='error', timeout=5)
            self.app.call_from_thread(self.dismiss, 'cancelled')

    def set_finished(self):
        self.query_one('#progress-finish-container').display = 'block'
        self.query_one('#progress-cancel-container').display = 'none'

    def update_instances(self):
        registry = InstanceRegistry.load()
        try:
            registry.add_instance(
                instance_id=self.instance.instance_id,
                name=self.instance.name,
                status='stopped',
                created=self.instance.install_date,
                pack_version=self.instance.modpack_version,
                modloader=self.instance.modloader,
                minecraft_version=self.instance.minecraft_version,
                path=self.instance.path
            )
            registry.save()
        except ValueError as e:
            def overwrite_instance(result: bool | None) -> None:
                if result:
                    registry.remove_instance(self.instance.instance_id)
                    registry.add_instance(
                        instance_id=self.instance.instance_id,
                        name=self.instance.name,
                        status='stopped',
                        created=self.instance.install_date,
                        pack_version=self.instance.modpack_version,
                        modloader=self.instance.modloader,
                        minecraft_version=self.instance.minecraft_version,
                        path=self.instance.path
                    )
                    registry.save()
            self.notify(f"Instance with ID '{self.instance.instance_id}' already in registry", severity='warning', timeout=5)
            self.app.push_screen(DeleteModal(f"Overwrite Entry for Instance ID '{self.instance.instance_id}'?"), overwrite_instance)
        return

    def progress_bar_callback(self, total: int, progress: int, bar_id: int=1, step: int=0):
        bar_map = [self.progress_bar, self.sub_progress_bar]
        step_list = [0, 22, 11, 11, 11, 6, 33, 6]
        bar_map[bar_id].update(total=total, progress=progress)
        if bar_id == 1 and step and self.sub_progress_bar.progress and self.sub_progress_bar.total:
            sub_progress_percent = int(self.sub_progress_bar.progress) / int(self.sub_progress_bar.total)
            self.progress_bar.update(progress=sum(step_list[:step]) + step_list[step] * sub_progress_percent)

    def step_callback(self, step: str, label_id: int=1):
        label_map = [self.progress_step, self.progress_substep]
        label = label_map[label_id]
        label.update(step)
