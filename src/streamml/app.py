from textual.app import App, ComposeResult
from textual.widgets import TabbedContent, TabPane
from textual.theme import Theme

from pathlib import Path
import os

from .front.detector_tab import DetectorTab
from .front.detector_profiles_tab import DetectorProfilesTab
from .front.options_tab import OptionsTab

from .back.detector_profiles_manager import DetectorProfilesManager


XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))

theme = Theme(
    name="pastel_blue_theme",        
    primary="#82A6F2",      
    secondary="#778899",    
    accent="#E0FFFF",       
    # background="#1a1b26", 
    surface="#1e1e20",      
    error="#ffb3ba",        
    success="#baffc9",      
    warning="#ffffba",      
)

class Streamml(App):
    CSS_PATH = "styles/styles.css"

    def __init__(self):
        super().__init__()
        self.detector_profiles_manager = DetectorProfilesManager(profiles_file=f"{XDG_DATA_HOME}/netmonitor/objects/detector_profiles_objects")

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane(title="Detector", id="detector", classes="detector-theme"):
                with TabbedContent():
                    with TabPane(title="Models"):
                        yield DetectorTab(self.manager.detector_profiles_manager)
                    with TabPane(title="Profiles"):
                        yield DetectorProfilesTab(self.manager.detector_profiles_manager)
            
            with TabPane(title="Options", id="options", classes="options-theme"):
                yield OptionsTab(self.detector_profiles_manager) 

    def on_mount(self):
        self.register_theme(theme)  
        self.theme = "pastel_blue_theme"

    @property
    def manager(self):
        return self

def main():
    Streamml().run()

if __name__ == "__main__":
    main()
