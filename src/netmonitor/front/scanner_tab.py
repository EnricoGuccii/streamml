from textual import on 
from textual.app import ComposeResult
from textual.widgets import Checkbox, Input, Select, Button, Label, SelectionList, Pretty
from textual.widgets.selection_list import Selection
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.events import Mount

import psutil, ipaddress, shlex 
from typing import List, Dict, Optional

from ..back.scanner_profiles_manager import ScannerProfilesManager
from .scanner_tab_pushscreens import SaveProfilePushScreen

class ScannerTab(Container):

    def __init__(self, manager: ScannerProfilesManager):
        super().__init__()
        self.manager = manager
        self.manager.on_message = self.on_manager_message

    def compose(self) -> ComposeResult:
        friendly_section = Container(id="friendly-command-section", classes="section card")
        friendly_section.border_title = "Scanner Configuration"
        
        with friendly_section:
            yield Label("Interface:", classes="label")
            try:
                interfaces = list(psutil.net_if_addrs().keys())
            except Exception:
                interfaces = []
            
            yield Select.from_values(
                interfaces,
                id="interface-select",
                allow_blank=False,
                classes="input"
            )

            yield Label("IP address:", classes="label")
            yield Input(
                value="127.0.0.1/32",
                placeholder="192.168.0.0/24",
                name="ip-input",
                id="ip",
                classes="input"
            )

            yield Label("Port range (or single port)", classes="label")
            with Horizontal(id="port-range", classes="input-row"):
                yield Input(placeholder="Start / Single", id="low-port-range", classes="input half")
                yield Input(placeholder="End (Optional)", id="high-port-range", classes="input half")

            yield Checkbox("Check for CVE's", id="cve-checkbox", classes="checkbox")

            yield Label("Scan options:", classes="label")
            with Horizontal(classes="selection-row"):
                yield SelectionList[str](
                    Selection("Service version (-sV)", "-sV", False),
                    Selection("OS detection (-O)", "-O", False),
                    Selection("SYN scan (-sS)", "-sS", False),
                    Selection("UDP scan (-sU)", "-sU", False),
                    Selection("Fast scan (-F)", "-F", False),
                    Selection("Aggressive scan (-A)", "-A", False),
                    Selection("Ping skip (-Pn)", "-Pn", False),
                    Selection("Timing T4 (-T4)", "-T4", True),
                    classes="selection-list"
                )

        user_section = Container(id="user-command-section", classes="section card")
        user_section.border_title = "Manual Command"
        
        with user_section:
            yield Input(
                placeholder="sudo nmap -sS 192.168.1.1",
                name="user-nmap-input",
                id="usercommand",
                classes="input full"
            )

        
        final_section = Container(id="final-section", classes="section card")
        final_section.border_title = "Execution"
        
        with final_section:
            with Vertical(id="final-command", classes="command-output"):
                self.final_command = Pretty([], id="final-command-output")
                yield self.final_command
            with Vertical(id="buttons", classes="buttons-column"):
                yield Button("Scan now", id="scan-button", variant="success") 
                yield Button("Save profile", id="save-button", variant="primary")

        results_section = Container(id="results-section", classes="section card")
        results_section.border_title = "Scan Output"
        
        with results_section:
            with VerticalScroll(id="results-scroll"):
                self.results = Pretty([], id="results", classes="results")
                yield self.results

    def validate_inputs(self, nmap_input: Dict[str, str]) -> List[str]: 
        errors: List[str] = []

        if self.query_one("#cve-checkbox", Checkbox).value:
            args = nmap_input.get("arguments", "")
            if "-sV" not in args.split():
                errors.append("To check for CVE's, '-sV' option is required")
                return errors

        targets = nmap_input.get("targets", "").strip()
        if not targets:
            errors.append("IP field cannot be empty")
            return errors
        
        if not self.query_one("#usercommand", Input).value.strip():
            try:
                ipaddress.ip_network(targets, strict=False)
            except ValueError:
                errors.append(f"Invalid IP address/CIDR: {targets}")
                return errors

        if "ports" in nmap_input:
            port_str = nmap_input["ports"]
            if "-" in port_str:
                try:
                    low, high = map(int, port_str.split("-"))
                    if not (1 <= low <= 65535 and 1 <= high <= 65535):
                        errors.append("Ports must be in range 1-65535")
                    if low > high:
                        errors.append("Start port cannot be greater than end port")
                except ValueError:
                    errors.append("Ports (range) must be numbers")
            else:
                try:
                    port = int(port_str)
                    if not (1 <= port <= 65535):
                        errors.append("Port must be in range 1-65535")
                except ValueError:
                    errors.append("Port must be a number")

        dry_run_err = self.dry_run_nmap_command(nmap_input)
        if dry_run_err:
            errors.append(dry_run_err)
        return errors

    def dry_run_nmap_command(self, nmap_input: Dict[str, str]) -> Optional[str]:
        try:
            cmd = ["nmap"]
            if "arguments" in nmap_input:
                cmd += shlex.split(nmap_input["arguments"])
            if "ports" in nmap_input:
                cmd += ["-p", nmap_input["ports"]]
            cmd.append(nmap_input["targets"])
            return None 
        except Exception as e:
            return f"Błąd weryfikacji komendy: {e}"

    def get_nmap_input(self, return_dict: bool = False) -> list[str] | dict:
        user_command = self.query_one("#usercommand", Input).value.strip()
        low_port = self.query_one("#low-port-range", Input).value.strip()
        high_port = self.query_one("#high-port-range", Input).value.strip()
        interface = self.query_one("#interface-select", Select).value
        targets = self.query_one("#ip", Input).value.strip()
        options = self.query_one(SelectionList).selected  

        if return_dict:
            if user_command:
                parts = shlex.split(user_command)
                
                if parts and parts[0] == "sudo": parts.pop(0)
                if parts and parts[0] == "nmap": parts.pop(0)
                
                if not parts:
                    return {}

                target = parts[-1]
                args = parts[:-1]
                
                return {
                    "targets": target,
                    "arguments": " ".join(args)
                }
            else:
                nmap_dict = {"targets": targets}
                
                if low_port:
                    if high_port:
                        nmap_dict["ports"] = f"{low_port}-{high_port}"
                    else:
                        nmap_dict["ports"] = f"{low_port}"

                args: list[str] = []
                if options:
                    args.extend(options)           
                if interface:
                    args.extend(["-e", str(interface)]) 
                if args:
                    nmap_dict["arguments"] = " ".join(args)

                return {k: v for k, v in nmap_dict.items() if v is not None}

        if user_command: 
            return shlex.split(user_command)

        parts = ["nmap"]
        if interface:
            parts.extend(["-e", str(interface)])
        if options:
            parts.extend(options)
        
        if low_port:
            if high_port:
                parts.extend(["-p", f"{low_port}-{high_port}"])
            else:
                parts.extend(["-p", f"{low_port}"])
                
        parts.append(targets)
        return parts

    @on(Mount)
    @on(SelectionList.SelectedChanged)
    @on(Input.Changed)
    @on(Select.Changed)
    def update_selected_view(self, event=None) -> None:
        self.final_command.update(" ".join(self.get_nmap_input()))

    @on(Button.Pressed, "#scan-button")
    async def handle_scan_button(self, event: Button.Pressed) -> None:
        nmap_input = self.get_nmap_input(return_dict=True)
        if not isinstance(nmap_input, dict):
            self.notify("Błąd: dane wejściowe nie są słownikiem", severity="error")
            return
        errors = self.validate_inputs(nmap_input)
        if errors:
            self.notify("\n".join(errors), title="Bad Input", severity="error")
        else:
            try:
                temp_prof_name = "temp_scan_profile" 
                self.notify("Start scanning", title="Notification", severity="information")
                
                if not self.manager.add_profile(temp_prof_name, notify=False):
                    self.notify("Błąd: Nie udało się utworzyć profilu (problem z zapisem pliku?)", severity="error")
                    return

                if not self.manager.update_profile(temp_prof_name, "nmap_input", nmap_input, notify=False):
                    self.notify("Błąd: Nie udało się zaktualizować parametrów skanowania", severity="error")
                    self.manager.delete_profile(temp_prof_name, notify=False)
                    return
                
                profile = self.manager.get_profile(temp_prof_name)
                if profile:
                    scan_now_results = profile.scan()
                    self.results.update(scan_now_results)
                    self.manager.delete_profile(temp_prof_name, notify=False)
                    self.notify("Scanning completed", title="Notification", severity="information")
                else:
                    self.notify("Krytyczny błąd: Profil zniknął po utworzeniu", severity="error")

            except Exception as e:
                self.notify(f"Scanner error: {e}", title="Error", severity="error")

    @on(Button.Pressed, "#save-button")
    async def handle_save_button(self, event: Button.Pressed):
        nmap_input = self.get_nmap_input(return_dict=True)
        if not isinstance(nmap_input, dict):
            self.notify("Błąd: dane wejściowe nie są słownikiem", severity="error")
            return

        errors = self.validate_inputs(nmap_input)
        if errors:
            self.notify("\n".join(errors), title="Bad Input", severity="error")
            return

        cve_check = self.query_one("#cve-checkbox", Checkbox).value
        self.app.push_screen(SaveProfilePushScreen(self.manager, nmap_input, cve_check))

    def on_manager_message(self, msg: str, title: str, severity):
        self.app.notify(message=msg, title=title, severity=severity)
