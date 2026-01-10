from textual.app import ComposeResult
from textual.widgets import Input, Label, Button
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual import on

from ..back.detector_profiles_manager import DetectorProfilesManager

class SaveProfilePushScreen(ModalScreen[str]):
    def __init__(self, manager: DetectorProfilesManager, input_data , *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.input_data = input_data


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
            self.manager.add_profile(profile_name,self.input_data)
            self.dismiss(None)
        else:
            self.dismiss(None)
