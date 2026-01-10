from textual import on 
from textual.app import ComposeResult
from textual.widgets import Input, Button, Label 
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen

from ..back.scanner_profiles_manager import ScannerProfilesManager

class SaveProfilePushScreen(ModalScreen[str]):
    def __init__(self, manager: ScannerProfilesManager, nmap_input, cve_check, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.nmap_input = nmap_input
        self.cve_check = cve_check


    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-window small-modal"):
            yield Label("Save scan profile", classes="modal-header")
            yield Input(placeholder="Profile name:", id="profile-name", classes="input")
            with Horizontal(id="buttons-row", classes="modal-buttons modal-footer"):
                yield Button("Confirm", id="confirm-button", variant="success", classes="button")
                yield Button("Cancel", id="cancel-button", variant="error", classes="button")

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "confirm-button":
            profile_name = self.query_one("#profile-name", Input).value.strip()
            self.manager.add_profile(profile_name)
            self.manager.update_profile(profile_name,"nmap_input",self.nmap_input,notify=False)
            self.manager.update_profile(profile_name,"cve",self.cve_check, notify=False)
            self.dismiss(None)
        else:
            self.dismiss(None)

