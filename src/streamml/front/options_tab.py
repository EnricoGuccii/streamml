from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Input, Label
from textual import on

from ..back.notification_service import notification_service

class OptionsTab(Container):
    def __init__(self, detector_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detector_manager = detector_manager

    def compose(self) -> ComposeResult:
        notify_section = Container(id="notify-section", classes="section-card")
        notify_section.border_title = "Notification config"
        with notify_section:  
            yield Label("Discord Webhook URL:")
            yield Input(placeholder="https://discord.com/api/webhooks/...", id="input-webhook-url")
            
            with Horizontal(classes="modal-footer"):
                yield Button("Save config", id="save-config", variant="success")
                yield Button("notification test", id="test-notif", variant="primary")

    def on_mount(self):
        self.query_one("#input-webhook-url", Input).value = notification_service.webhook_url

    @on(Button.Pressed, "#save-config")
    def save_configuration(self):
        url = self.query_one("#input-webhook-url", Input).value.strip()
        
        if notification_service.save_config(url):
            self.app.notify("Config saved", severity="information")
        else:
            self.app.notify("Error during saving", severity="error")

    @on(Button.Pressed, "#test-notif")
    def test_notification(self):
        success = notification_service.send_message("**Test NetMonitor**\n")
        
        if success:
            self.app.notify("good", severity="information")
        else:
            self.app.notify("bad", severity="error")
