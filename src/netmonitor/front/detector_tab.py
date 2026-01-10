from textual import on
from textual.app import ComposeResult
from textual.widgets import Input, Select, Button, Label, Checkbox
from textual.containers import Container, Horizontal, Vertical, VerticalScroll

import psutil

from ..back.detector_profiles_manager import DetectorProfilesManager
from ..back.window import FEATURE_LIST
from ..front.detector_tab_pushscreens import SaveProfilePushScreen

class DetectorTab(Container):
    def __init__(self, manager: DetectorProfilesManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.manager.on_message = self.on_manager_message

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-config-container"):
            
            model_section = Container(id="model-section", classes="section-card")
            model_section.border_title = "Algorithm: HalfSpaceTrees"
            with model_section:
                with VerticalScroll(classes="detector-scroll"):
                    yield Label("Select interface:", classes="label")
                    try:
                        ifaces = list(psutil.net_if_addrs().keys())
                    except:
                        ifaces = []
                    
                    yield Select.from_values(
                        ifaces,
                        id="interface-select",
                        allow_blank=False,
                        classes="input"
                    )
                    
                    yield Label("Model params:", classes="label")
                    yield Input(placeholder="Trees number (int, def: 10)", id="param-trees", classes="input")
                    yield Input(placeholder="Height (int, def: 8)", id="param-height", classes="input")
                    yield Input(placeholder="Window size (int, def: 250)", id="param-window", classes="input")
                    yield Input(placeholder="Seed (int, def: 42)", id="param-seed", classes="input")
                    yield Input(placeholder="Window duration (def: 10 sec )", id="param-window_duration", classes="input")
                    yield Input(placeholder="Threshold (0.0 - 1.0, def: 0.7)", id="param-threshold", classes="input")
                    yield Input(placeholder="Queue size (int, def: 10000)", id="param-queue_size", classes="input")

            features_section = Container(id="features-section", classes="section-card")
            features_section.border_title = "Flow-based Features"
            with features_section:
                with VerticalScroll(classes="detector-scroll"):
                    yield Label("Select features to include in model:", classes="label")
                    self.feature_checkboxes = {}
                    for feat in FEATURE_LIST:
                        cb = Checkbox(feat, value=True, classes="input")
                        self.feature_checkboxes[feat] = cb
                        yield cb

        bpf_section = Container(id="bpf-section", classes="section-card")
        bpf_section.border_title = "BPF Filter (Optional)"
        with bpf_section:
            yield Input(
                placeholder="BPF Filter (e.g. 'tcp port 80 or udp')", 
                id="param-bpf_filter", 
                classes="input full"
            )
        with Container(classes="save-button-container"):
            yield Button("Save Profile", id="save-button", variant="success")

    def get_inputs(self):
        features = [f for f, cb in self.feature_checkboxes.items() if cb.value]

        if not features:
            raise ValueError("Select at least one feature.")

        params = {}
        
        try:
            interface = self.query_one("#interface-select", Select).value
            if not interface:
                raise ValueError("Select interface.")
            params["interface"] = interface
        except Exception:
            raise ValueError("Interface selection error.")

        bpf_input = self.query_one("#param-bpf_filter", Input)
        if bpf_input.value.strip():
            params["bpf_filter"] = bpf_input.value.strip()

        defaults = {
            "trees": 10,
            "height": 8,
            "window": 250,
            "seed": 42,
            "threshold": 0.7,
            "window_duration": 10.0,
            "queue_size": 10000,
            "bpf_filter": ""
        }

        model_section = self.query_one("#model-section")
        for inp in model_section.query("Input"):
            if inp.id and inp.id.startswith("param-"):
                key = inp.id.removeprefix("param-")
                if key == "bpf_filter": continue

                val_str = inp.value.strip()
                
                if not val_str:
                    if key in defaults and defaults[key] is not None:
                        params[key] = defaults[key]
                    continue

                try:
                    if key in ["trees", "height", "window", "seed","queue_size"]:
                        params[key] = int(val_str)
                    elif key in ["threshold", "window_duration"]:
                        params[key] = float(val_str)
                except ValueError:
                    raise ValueError(f"Param '{key}' must be a number.")

        return {
            "features": features,
            "params": params,
        }

    @on(Button.Pressed, "#save-button")
    async def handle_save_button(self, event: Button.Pressed):
        try:
            input_data = self.get_inputs()
            self.app.push_screen(SaveProfilePushScreen(self.manager, input_data=input_data))
        except ValueError as e:
            self.app.notify(str(e), title="Validation error", severity="error")

    def on_manager_message(self, msg: str, title: str, severity):
        self.app.notify(message=msg, title=title, severity=severity)
