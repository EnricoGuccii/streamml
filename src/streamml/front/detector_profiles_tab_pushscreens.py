from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Pretty, DataTable, Switch
from textual.containers import Vertical, Horizontal, VerticalScroll, Container
from textual_plotext import PlotextPlot

from datetime import datetime

from ..back.detector_profiles_manager import DetectorProfilesManager
from ..back.detector_profile_HST import DetectorProfileHST

class PlotTab(Container):
    def __init__(self, profile: DetectorProfileHST, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile
        self.classes = "plot-card" 

    def compose(self):
        yield PlotextPlot()

    def on_mount(self):
        self.set_interval(1, self.update_plot)

    def update_plot(self):
        plot_widget = self.query_one(PlotextPlot)
        plt = plot_widget.plt
        
        y = list(getattr(self.profile, "plot_data", []))

        plt.clear_figure()
        plt.theme("dark") 
        
        plt.plot(y, marker="dot", color="green")
        plt.title("Anomaly Score")
        plt.ylabel("last 30 windows")
        plt.ylim(0, 1)
        
        threshold = self.profile.params.get("threshold", 0.7)
        if threshold is not None:
            plt.horizontal_line(float(threshold), color="red")


        plot_widget.refresh()


class ShowProfilePushScreen(ModalScreen[str]):
    def __init__(self, manager, profile_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.profile_name = profile_name
        self.profile = self.manager.get_profile(profile_name)

    def compose(self) -> ComposeResult:
        with Container(classes="modal-window large-modal"):
            yield Label(f"Profile: {self.profile_name}", classes="modal-header")
            
            with Horizontal(classes="modal-split-container"):
                
                with Vertical(classes="left-panel"):
                    yield PlotTab(self.profile)
                
                with Vertical(classes="right-panel"):
                    yield Label("Runtime Stats (Live)", classes="section-header")
                    with VerticalScroll(classes="info-box", id="stats-box"):
                        yield Pretty({}, id="runtime-stats-pretty")

                    yield Label("Configuration", classes="section-header")
                    with VerticalScroll(classes="info-box"):
                        yield Pretty(self.profile.to_dict())
                    
                    with Container(classes="modal-footer"):
                        yield Button("Close", id="cancel-button", variant="primary")

    def on_mount(self):
        self.set_interval(1.0, self.update_stats)
        self.update_stats() 

    def update_stats(self):
        if self.profile:
            stats = self.profile.get_runtime_stats()
            self.query_one("#runtime-stats-pretty", Pretty).update(stats)

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(None)


class ShowLogsPushScreen(ModalScreen[str]):
    def __init__(self, manager: DetectorProfilesManager, profile_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.profile_name = profile_name

    def compose(self) -> ComposeResult:
        with Container(classes="modal-window medium-modal"):
            yield Label(f"Anomaly Logs: {self.profile_name}", classes="modal-header")
            
            with Container(classes="table-container"):
                yield DataTable(id="logs_table", zebra_stripes=True, cursor_type="row")
            
            with Horizontal(classes="modal-footer"):
                yield Button("Clear History", id="clear-button", variant="warning")
                yield Button("Close", id="cancel-button", variant="primary")


    def on_mount(self):
        table = self.query_one("#logs_table", DataTable)
        table.add_columns("Timestamp", "Score", "Packets Rate", "Protocol Info", "Verdict")
        
        logs = self.manager.get_profile_logs(self.profile_name)
        
        if not logs:
            return

        sorted_logs = sorted(logs, key=lambda x: x.get("ts", 0), reverse=True)

        for log in sorted_logs:
            dt = datetime.fromtimestamp(log.get("ts", 0)).strftime("%Y-%m-%d %H:%M:%S")
            
            score = f"{log.get('score', 0):.4f}"
            rate = f"{log.get('pkt_rate', 0):.1f}"
            proto = str(log.get("proto_info", "-"))
            verdict = "ANOMALY" 
            
            table.add_row(dt, score, rate, proto, verdict)

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "clear-button":
            profile = self.manager.get_profile(self.profile_name)
            if profile:
                profile.clear_logs()
                self.query_one("#logs_table", DataTable).clear()
        else:
            self.dismiss(None)

class SetDetectorNotificationPushScreen(ModalScreen[str]):
    def __init__(self, manager, profile_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.profile_name = profile_name
        self.profile = self.manager.get_profile(profile_name)

    def compose(self) -> ComposeResult:
        current_val = getattr(self.profile, 'notify_enabled', False)
        
        with Container(classes="modal-window small-modal"):
            yield Label(f"Notification: {self.profile_name}", classes="modal-header")
            
            with Vertical(classes="section-card"):
                yield Label("Enable notification (Discord)")
                yield Switch(value=current_val, id="switch-anomaly")

            with Horizontal(classes="modal-footer"):
                yield Button("Close", id="close-button", variant="primary")

    @on(Switch.Changed)
    def on_switch_changed(self, event: Switch.Changed):
        if event.switch.id == "switch-anomaly":
            self.profile.notify_enabled = event.value
            self.manager.try_save_profiles(notify=False)

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(None)

class ConfirmDeletePushScreen(ModalScreen[str]):
    def __init__(self, manager: DetectorProfilesManager, profile_name:str, *args, **kwargs):
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
