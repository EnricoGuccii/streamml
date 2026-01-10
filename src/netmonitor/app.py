from textual.app import App, ComposeResult
from textual.widgets import TabbedContent, TabPane
from textual.theme import Theme

from apscheduler.schedulers.background import BackgroundScheduler
from pathlib import Path
import os

from .front.scanner_tab import ScannerTab
from .front.scanner_profiles_tab import ScannerProfilesTab
from .front.detector_tab import DetectorTab
from .front.detector_profiles_tab import DetectorProfilesTab
from .front.options_tab import OptionsTab

from .back.scanner_profiles_manager import ScannerProfilesManager
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

class NetMonitor(App):
    CSS_PATH = "styles/styles.css"

    def __init__(self):
        super().__init__()
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.scanner_profiles_manager = ScannerProfilesManager(profiles_file=f"{XDG_DATA_HOME}/netmonitor/objects/scanner_profiles_objects", scheduler=self.scheduler)
        self.detector_profiles_manager = DetectorProfilesManager(profiles_file=f"{XDG_DATA_HOME}/netmonitor/objects/detector_profiles_objects")

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane(title="Scanner", id="scanner", classes="scanner-theme"):
                with TabbedContent():
                    with TabPane(title="Scan"):
                        yield ScannerTab(self.manager.scanner_profiles_manager)
                    with TabPane(title="Profiles"):
                        yield ScannerProfilesTab(self.manager.scanner_profiles_manager)

            with TabPane(title="Detector", id="detector", classes="detector-theme"):
                with TabbedContent():
                    with TabPane(title="Models"):
                        yield DetectorTab(self.manager.detector_profiles_manager)
                    with TabPane(title="Profiles"):
                        yield DetectorProfilesTab(self.manager.detector_profiles_manager)
            
            with TabPane(title="Options", id="options", classes="options-theme"):
                yield OptionsTab(self.scanner_profiles_manager, self.detector_profiles_manager) 

    def on_mount(self):
        self.register_theme(theme)  
        self.theme = "pastel_blue_theme"

    @property
    def manager(self):
        return self

def main():
    NetMonitor().run()

if __name__ == "__main__":
    main()
