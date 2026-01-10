from textual.app import ComposeResult
from textual import on
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Pretty, Select, Switch
from textual.containers import Vertical, Horizontal, VerticalScroll, Container

from ..back.scanner_profiles_manager import ScannerProfilesManager

class ScanNowPushScreen(ModalScreen[str]):
    def __init__(self, manager: ScannerProfilesManager, profile_name:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.profile_name = profile_name

    def compose(self) -> ComposeResult:
        with Container(classes="modal-window large-modal"):
            yield Label(f"Scanning: {self.profile_name}", classes="modal-header")
            with VerticalScroll(classes="info-box"):
                yield Pretty(self.manager.get_profile(self.profile_name).scan())
            with Horizontal(classes="modal-footer"):
                yield Button("Close", variant="primary")

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

class ShowProfilePushScreen(ModalScreen[str]):
    def __init__(self, manager: ScannerProfilesManager, profile_name:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.profile_name = profile_name

    def compose(self) -> ComposeResult:
        with Container(classes="modal-window medium-modal"):
            yield Label(f"Profile: {self.profile_name}", classes="modal-header")
            with VerticalScroll(classes="info-box"):
                yield Pretty(self.manager.get_profile(self.profile_name).to_dict())
            with Horizontal(classes="modal-footer"):
                yield Button("Close", id="cancel-button", variant="primary")

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class SetSchedulerPushScreen(ModalScreen[str]):
    def __init__(self, manager: ScannerProfilesManager, profile_name:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.profile_name = profile_name

    def compose(self) -> ComposeResult:
        with Container(classes="modal-window small-modal"):
            yield Label("Set CRON Scheduler", classes="modal-header")
            yield Label("Format: min hour day month day_of_week", classes="label")
            yield Input(placeholder="* * * * * ", id="cron-input", classes="input")
            
            with Horizontal(classes="modal-footer"):
                yield Button("Confirm", id="confirm-button", variant="success")
                yield Button("Cancel", id="cancel-button", variant="error")

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "confirm-button":
            cron_input = self.query_one("#cron-input", Input).value.strip()
            if cron_input:
                self.manager.set_validated_scheduler(self.profile_name, cron_input)
            self.dismiss(None)
        else:
            self.dismiss(None)

class SetNotifacationOptionsPushScreen(ModalScreen[str]):
    def __init__(self, manager: ScannerProfilesManager, profile_name:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.profile_name = profile_name
        self.profile = self.manager.get_profile(profile_name)

    def compose(self) -> ComposeResult:
        current_enabled = getattr(self.profile, 'notify_enabled', False)
        current_cve_only = getattr(self.profile, 'notify_only_cve', False)

        with Container(classes="modal-window small-modal"):
            yield Label(f"Notifications: {self.profile_name}", classes="modal-header")
            
            with Vertical(classes="section-card"):
                yield Label("Enable notifications (Discord):")
                yield Switch(value=current_enabled, id="switch-enable")
                
                yield Label("Notify only when scanner finds CVE")
                yield Switch(value=current_cve_only, id="switch-cve-only")

            with Horizontal(classes="modal-footer"):
                yield Button("Close", id="close-button", variant="primary")

    @on(Switch.Changed)
    def on_switch_changed(self, event: Switch.Changed):
        if event.switch.id == "switch-enable":
            self.profile.notify_enabled = event.value
        elif event.switch.id == "switch-cve-only":
            self.profile.notify_only_cve = event.value
            
        self.manager.try_save_profiles(notify=False)

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(None)

class ShowLogsPushScreen(ModalScreen[str]):
    def __init__(self, manager: ScannerProfilesManager, profile_name:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.profile_name = profile_name
        self.logs = []

    def compose(self) -> ComposeResult:
        with Container(classes="modal-window large-modal"):
            yield Label(f"Logs: {self.profile_name}", classes="modal-header")
            
            yield Select([], prompt="Select date", id="scan-date-select")
            
            with VerticalScroll(classes="info-box"):
                yield Pretty({}, id="log-content")
            
            with Horizontal(classes="modal-footer"):
                yield Button("Close", id="cancel-button", variant="primary")

    def on_mount(self):
        self.logs = self.manager.get_profile_logs(self.profile_name)
        select = self.query_one("#scan-date-select", Select)
        options = []
        
        if self.logs:
            for index, log in enumerate(reversed(self.logs)):
                real_index = len(self.logs) - 1 - index
                label = log.get('_timestamp', f"Scan #{real_index + 1} (no date)")
                
                options.append((str(label), real_index))
            
            select.set_options(options)
            
            if options:
                select.value = options[0][1]

    @on(Select.Changed, "#scan-date-select")
    def on_date_selected(self, event: Select.Changed):
        if event.value is not None:
            index = event.value
            if index == Select.BLANK:
                self.query_one("#log-content", Pretty).update({})
                return
            if 0 <= index < len(self.logs):
                log_entry = self.logs[index]
                self.query_one("#log-content", Pretty).update(log_entry)

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class ConfirmDeletePushScreen(ModalScreen[str]):
    def __init__(self, manager: ScannerProfilesManager, profile_name:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.profile_name = profile_name

    def compose(self) -> ComposeResult:
        with Container(classes="modal-window small-modal"):
            yield Label("Are you sure?",classes="modal-header")
            with Horizontal(classes="modal-footer"):
                yield Button("Delete", id="confirm-button", variant="error")
                yield Button("Cancel", id="cancel-button", variant="default")

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "confirm-button":
            self.manager.delete_profile(self.profile_name)
            self.dismiss(None)
        else:
            self.dismiss(None)
