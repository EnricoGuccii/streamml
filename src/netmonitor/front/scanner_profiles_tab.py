from textual.widgets import Button, Label, Switch 
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll

from ..back.scanner_profiles_manager import ScannerProfilesManager
from .scanner_profiles_tab_pushscreens import ScanNowPushScreen, SetSchedulerPushScreen, ShowLogsPushScreen, SetNotifacationOptionsPushScreen, ShowProfilePushScreen, ConfirmDeletePushScreen

class ScannerProfilesTab(Vertical):
    def __init__(self, manager: ScannerProfilesManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.manager.on_refresh = self.refresh_profiles
        self.manager.on_message = self.on_manager_message

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="profiles-list")

    def on_mount(self) -> None:
        self.refresh_profiles()

    def refresh_profiles(self) -> None:
        profiles_list = self.query_one("#profiles-list", VerticalScroll)
        profiles_list.remove_children()

        if not self.manager.profiles:
            return

        for profile in self.manager.profiles:
            row = Horizontal(
                Switch(id=f"switch-{profile.profile_name}", value=profile.is_active),
                Button("Scan Now", id=f"scan-now-button-{profile.profile_name}", classes="profile-action", variant="success"),
                Label(f"{profile.profile_name}", classes="profile-profile_name"),
                Button("Show Profile", id=f"show-profile-button-{profile.profile_name}", classes="profile-action", variant="primary"),
                Button("Show logs", id=f"show-logs-button-{profile.profile_name}", classes="profile-action", variant="default"),
                Button("Set scheduler", id=f"set-scheduler-button-{profile.profile_name}", classes="profile-action", variant="default"),
                Button("Notifications", id=f"set-notifications-button-{profile.profile_name}", classes="profile-action", variant="default"),
                Button("Delete", id=f"delete-{profile.profile_name}", classes="profile-action", variant="error"),
                classes="profile-row"
            )
            profiles_list.mount(row)

    @on(Switch.Changed)
    def switch_changed(self, event: Switch.Changed) -> None:
        switch_id = event.switch.id
        if not switch_id:
            return
        profile_name = switch_id.removeprefix("switch-")

        if event.switch.value:
            is_turned_on = self.manager.turn_on_profile(profile_name)
            if not is_turned_on:
                event.switch.value = False
        else:
            is_turned_off = self.manager.turn_off_profile(profile_name)
            if not is_turned_off:
                event.switch.value = False

    @on(Button.Pressed)
    def on_any_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if not button_id:
            return
        if button_id.startswith("scan-now-button-"):
            profile_name = button_id.removeprefix("scan-now-button-")
            self.app.push_screen(ScanNowPushScreen(self.manager, profile_name))
        elif button_id.startswith("show-profile-button-"):
            profile_name = button_id.removeprefix("show-profile-button-")
            self.app.push_screen(ShowProfilePushScreen(self.manager, profile_name))
        elif button_id.startswith("set-scheduler-button-"):
            profile_name = button_id.removeprefix("set-scheduler-button-")
            self.app.push_screen(SetSchedulerPushScreen(self.manager, profile_name))
        elif button_id.startswith("set-notifications-button-"):
            profile_name = button_id.removeprefix("set-notifications-button-")
            self.app.push_screen(SetNotifacationOptionsPushScreen(self.manager, profile_name))
        elif button_id.startswith("delete-"):
            profile_name = button_id.removeprefix("delete-")
            self.app.push_screen(ConfirmDeletePushScreen(self.manager, profile_name))
        elif button_id.startswith("show-logs-button-"):
            profile_name = button_id.removeprefix("show-logs-button-")
            self.app.push_screen(ShowLogsPushScreen(self.manager, profile_name))

    def on_manager_message(self, msg: str, title: str, severity):
        self.app.notify(message=msg, title=title, severity=severity)
