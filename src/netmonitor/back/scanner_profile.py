import os
from pathlib import Path
from datetime import datetime
from tinydb import TinyDB
import nmap
from .notification_service import notification_service


XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
LOGS_PATH = f"{XDG_DATA_HOME}/netmonitor/scanner/profiles_logs"

class ScannerProfile:
    def __init__(self, profile_name: str, nmap_input=None, scheduler=None, cve=None):
        self.profile_name = profile_name  
        self.nmap_input = nmap_input or {}
        self.scheduler = scheduler
        self.cve = cve
        self.is_active = False
        
        self.notify_enabled = False
        self.notify_only_cve = False

        self.nm = None
        self.db = None
        self.profile_results_path = f"{LOGS_PATH}/{profile_name}.json"
        os.makedirs(os.path.dirname(self.profile_results_path), exist_ok=True)

    @property
    def nmap(self):
        if self.nm is None:
            self.nm = nmap.PortScanner()
        return self.nm

    @property
    def tinydb(self):
        if self.db is None:
            self.db = TinyDB(self.profile_results_path)
        return self.db

    def __getstate__(self):
        state = self.__dict__.copy()
        state['nm'] = None
        state['db'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.nm = None
        self.db = None

    def __repr__(self):
        return f"<ScannerProfile profile_name={self.profile_name!r}, active={self.is_active}>"


    def scan(self):
        targets = self.nmap_input.get("targets", "")
        arguments = self.nmap_input.get("arguments", "")
        ports = self.nmap_input.get("ports", "")

        if self.cve:
            arguments += " --script=vulners "

        if ports == '':
            self.nmap.scan(hosts=targets, arguments=arguments)
        else:
            self.nmap.scan(hosts=targets, ports=ports, arguments=arguments)

        xml_result = self.nmap.get_nmap_last_output()
        analyzed_results = self.nmap.analyse_nmap_xml_scan(xml_result)
        
        if isinstance(analyzed_results, dict):
            analyzed_results['_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        self.tinydb.insert(analyzed_results)

        if self.notify_enabled:
            self._handle_notification(analyzed_results, targets)

        return analyzed_results

    def _handle_notification(self, results, targets):
        scan_str = str(results).lower()
        found_issues = "cve" in scan_str or "vulnerab" in scan_str
        should_send = False
        msg = f"*Scanner report: {self.profile_name}*\nTargets: `{targets}`"
        summary = ""
        try:
            if 'scan' in results:
                for host, data in results['scan'].items():
                    summary += f"\n *{host}*"
                    
                    if 'tcp' in data:
                        open_ports = [f"{p}/tcp" for p, info in data['tcp'].items() if info.get('state') == 'open']
                        if open_ports:
                            summary += f"\n   Open ports: {', '.join(open_ports)}"
                    if 'udp' in data:
                        open_ports = [f"{p}/udp" for p, info in data['udp'].items() if info.get('state') == 'open']
                        if open_ports:
                            summary += f"\n   Open ports (UDP): {', '.join(open_ports)}"
                    if 'osmatch' in data and data['osmatch']:
                        os_name = data['osmatch'][0].get('name', 'Unknown')
                        summary += f"\n   OS detected: {os_name}"
        except Exception as e:
            summary += f"\n(Error building summary: {e})"

        if self.notify_only_cve:
            if found_issues:
                should_send = True
                msg += "\nCVE detected!"
                msg += "\n---" + summary
        else:
            should_send = True
            msg += "\nScan completed."
            if found_issues:
                msg += "\nPotential vulnerabilities detected."
            
            if summary:
                msg += "\n---" + summary

        if should_send:
            if len(msg) > 1900:
                msg = msg[:1900] + "\n...."
            notification_service.send_message(msg)


    def to_dict(self):
        return {
            "profile_name": self.profile_name,
            "nmap_input": self.nmap_input,
            "scheduler": self.scheduler,
            "is_active": self.is_active,
            "notify_enabled": getattr(self, 'notify_enabled', False),
            "notify_only_cve": getattr(self, 'notify_only_cve', False),
            "results_path": self.profile_results_path,
        }

    def get_logs(self):
        return self.tinydb.all()
