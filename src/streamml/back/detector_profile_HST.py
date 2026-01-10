import threading
import queue
import time
import os
from pathlib import Path
from scapy.all import wrpcap, AsyncSniffer 

from river.anomaly import HalfSpaceTrees
from tinydb import TinyDB
from tinydb.table import Document

from .window import Window
from .notification_service import notification_service

XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
LOGS_PATH = f"{XDG_DATA_HOME}/netmonitor/detector/profiles_logs"
PCAP_PATH = f"{XDG_DATA_HOME}/netmonitor/detector/profiles_pcaps"


class DetectorProfileHST:

    def __init__(
        self,
        profile_name: str,
        input_data: dict 
    ):
        self.profile_name = profile_name
        self.features = input_data.get("features", [])
        self.params = input_data.get("params", {})
        self.n_trees = int(self.params.get("trees", 10))
        self.height = int(self.params.get("height", 8))
        self.window_size = int(self.params.get("window", 250))
        self.seed = int(self.params.get("seed", 42))
        self.threshold = float(self.params.get("threshold", 0.7))
        self.window_duration = float(self.params.get("window_duration", 10.0))
        self.bpf_filter = self.params.get("bpf_filter", "")
        self.interface = self.params.get("interface", None)
        self.queue_size = int(self.params.get("queue_size", 10000))
        self.logs_path = f"{LOGS_PATH}/{profile_name}.json"
        os.makedirs(os.path.dirname(self.logs_path), exist_ok=True)
        
        self.is_active = False

        self.notify_enabled = False
        self._init_runtime_objects()


    def _init_runtime_objects(self):
        self.queue = queue.Queue(maxsize=self.queue_size)
        
        os.makedirs(f"{LOGS_PATH}", exist_ok=True)
        self.db = TinyDB(f"{LOGS_PATH}/{self.profile_name}.json")
        
        self.model = HalfSpaceTrees(
            n_trees=self.n_trees,
            height=self.height,
            window_size=self.window_size,
            seed=self.seed
        )

        self.window = Window(
            window_duration=self.window_duration, 
            enabled_features=self.features
        )
        
        self.processor_thread = None

        self.packets_read = 0      
        self.windows_analyzed = 0   
        
        if not hasattr(self, 'plot_data'):
            self.plot_data = []


    def __getstate__(self):
        state = self.__dict__.copy()
        cols_to_remove = ['sniffer_thread', 'processor_thread', 'queue', 'db', 'window']
        for col in cols_to_remove:
            if col in state:
                del state[col]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._init_runtime_objects()
        self.is_active = False 

    def __repr__(self):
        return f"<DetectorProfileHST profile_name={self.profile_name!r}, active={self.is_active}>"

    def turn_on(self):
        if self.is_active:
            return

        self.is_active = True
        os.makedirs(os.path.dirname(self.logs_path), exist_ok=True)
        self.window.window_duration = self.window_duration
        self.window.window_start = time.time()

        self.sniffer = AsyncSniffer(
            iface=self.interface,
            filter=self.bpf_filter,
            store=False,
            prn=self._add_to_queue
        )
        self.sniffer.start()

        self.processor_thread = threading.Thread(target=self._process_thread, daemon=True)

        self.processor_thread.start()

    def turn_off(self):
        self.is_active = False
        if self.sniffer:
            self.sniffer.stop()

        time.sleep(0.2)

    def _add_to_queue(self, pkt):
        if self.queue:
            try:
                self.queue.put_nowait(pkt)
                self.packets_read += 1
            except queue.Full:
                pass

    def _process_thread(self):
        while self.is_active:
            try:
                pkt = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            result = self.window.add_packet(pkt)

            if result is None:
                continue

            features, raw_packets = result
            self.windows_analyzed += 1
            
            if not features:
                continue

            sample = {feat: 0.0 for feat in self.features}
            for k, v in features.items():
                if k in sample:
                    sample[k] = float(v)

            score = self.model.score_one(sample)
            self.model.learn_one(sample)
            
            self.plot_data.append(score)
            if len(self.plot_data) > 30:
                self.plot_data.pop(0)

            if score > self.threshold:
                self._handle_anomaly(score, sample, raw_packets)

    def _handle_anomaly(self, score: float, features: dict, raw_packets: list):
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")

        os.makedirs(os.path.dirname(f"{PCAP_PATH}/{self.profile_name}"), exist_ok=True)
        filename = f"{PCAP_PATH}/{self.profile_name}/anom_{timestamp}.pcap"
        
        if raw_packets:
            try:
                wrpcap(filename, raw_packets)
            except Exception as e:
                print(f"Error saving pcap: {e}")

        if self.notify_enabled:
            msg = f"*Anomaly detected: {self.profile_name}*\nScore: `{score:.4f}`\nSaved: `{filename}`"
            notification_service.send_message(message=msg)

        if self.db:
            self.db.insert(
                Document({
                    "ts": time.time(),
                    "timestamp": timestamp,
                    "profile": self.profile_name,
                    "score": float(score),
                    "pcap": filename,
                    "pkt_rate": features.get("pkt_rate", 0),
                    "proto_info": f"TCP:{features.get('proto_tcp_ratio',0):.2f} UDP:{features.get('proto_udp_ratio',0):.2f}",
                }, doc_id=None)
            )

    def to_dict(self):
        return {
            "profile name": self.profile_name,
            "logs_path": self.logs_path,
            "pcap_path": f"{PCAP_PATH}/{self.profile_name}",
            "params": self.params,
            "features": self.features,
        }
        
    def get_logs(self):
        if self.db:
            return self.db.all()
        return []
        
    def clear_logs(self):
        if self.db:
            self.db.truncate()

    def get_runtime_stats(self):
        return {
            "is_active": self.is_active,
            "notify_enabled": self.notify_enabled,
            "packets_sniffed": getattr(self, "packets_read", 0),
            "queue_size": self.queue.qsize() if hasattr(self, "queue") and self.queue else 0,
            "windows_processed": getattr(self, "windows_analyzed", 0),
            "window_duration": self.window_duration
        }
