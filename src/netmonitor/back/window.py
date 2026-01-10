import time
from collections import defaultdict
from statistics import mean, pstdev
import math

from scapy.all import IP, IPv6, TCP, UDP, ICMP

class Window:
    def __init__(self, window_duration: float, enabled_features: list[str]):

        self.window_duration = float(window_duration)
        self.enabled = set(enabled_features)

        self.window_start = time.time()

        self.raw_packets_buffer = []

        self.flows = defaultdict(lambda: {
            "pkt_count": 0,
            "byte_count": 0,
            "dst_ports": defaultdict(int),
            "src_ports": defaultdict(int),
            "tcp_flags": {
                "syn": 0, "fin": 0, "rst": 0, "ack": 0,
                "psh": 0, "urg": 0, "xmas": 0, "null": 0,
            },
            "sizes": [],
            "start_ts": None,
            "end_ts": None,
            "tcp_pkts": 0,
            "udp_pkts": 0,
            "icmp_pkts": 0,
        })

    def add_packet(self, pkt):
        now = time.time()

        if now - self.window_start >= self.window_duration:
            features = self._finish_window()

            self.window_start = now
            
            raw = list(self.raw_packets_buffer)
            
            self.raw_packets_buffer.clear()
            self.flows.clear()

            self._process_single_packet(pkt)

            return features, raw

        self._process_single_packet(pkt)
        return None

    def _process_single_packet(self, pkt):
        self.raw_packets_buffer.append(pkt)

        proto = None
        if IP in pkt:
            src = pkt[IP].src
            dst = pkt[IP].dst
            proto = pkt[IP].proto
        elif IPv6 in pkt:
            src = pkt[IPv6].src
            dst = pkt[IPv6].dst
            proto = pkt[IPv6].nh
        else:
            return

        key = (src, dst, proto)
        f = self.flows[key]

        now = time.time()
        if f["start_ts"] is None:
            f["start_ts"] = now
        f["end_ts"] = now

        size = len(pkt)
        f["pkt_count"] += 1
        f["byte_count"] += size
        f["sizes"].append(size)

        if TCP in pkt:
            f["tcp_pkts"] += 1
            dport = pkt[TCP].dport
            sport = pkt[TCP].sport
            f["dst_ports"][dport] += 1
            f["src_ports"][sport] += 1

            flags = pkt[TCP].flags
            if flags & 0x02: f["tcp_flags"]["syn"] += 1
            if flags & 0x01: f["tcp_flags"]["fin"] += 1
            if flags & 0x04: f["tcp_flags"]["rst"] += 1
            if flags & 0x10: f["tcp_flags"]["ack"] += 1
            if flags & 0x08: f["tcp_flags"]["psh"] += 1
            if flags & 0x20: f["tcp_flags"]["urg"] += 1

            if flags in [0x29, 0x3F, 0x3B]:
                f["tcp_flags"]["xmas"] += 1
            if flags == 0:
                f["tcp_flags"]["null"] += 1

        elif UDP in pkt:
            f["udp_pkts"] += 1
            dport = pkt[UDP].dport
            sport = pkt[UDP].sport
            f["dst_ports"][dport] += 1
            f["src_ports"][sport] += 1

        elif ICMP in pkt:
            f["icmp_pkts"] += 1

    def _finish_window(self):
        if not self.flows:
            return {} 

        total_flows = len(self.flows)
        total_packets = 0
        total_bytes = 0

        tcp_flags_global = {
            "syn": 0, "fin": 0, "rst": 0, "ack": 0,
            "psh": 0, "urg": 0, "xmas": 0, "null": 0
        }

        all_sizes = []
        proto_tcp = 0
        proto_udp = 0
        proto_icmp = 0

        dst_port_counts = defaultdict(int)
        src_port_counts = defaultdict(int)

        for f in self.flows.values():
            total_packets += f["pkt_count"]
            total_bytes += f["byte_count"]

            for p, c in f["dst_ports"].items():
                dst_port_counts[p] += c
            for p, c in f["src_ports"].items():
                src_port_counts[p] += c

            for k in tcp_flags_global:
                tcp_flags_global[k] += f["tcp_flags"][k]

            all_sizes.extend(f["sizes"])
            proto_tcp += f["tcp_pkts"]
            proto_udp += f["udp_pkts"]
            proto_icmp += f["icmp_pkts"]

        window_len = self.window_duration
        total_pkts = total_packets if total_packets > 0 else 1
        
        feat = {}

        if "flow_count" in self.enabled: feat["flow_count"] = total_flows
        if "total_packets" in self.enabled: feat["total_packets"] = total_packets
        if "total_bytes" in self.enabled: feat["total_bytes"] = total_bytes
        if "avg_bytes_per_flow" in self.enabled: feat["avg_bytes_per_flow"] = total_bytes / total_flows if total_flows else 0
        if "pkt_rate" in self.enabled: feat["pkt_rate"] = total_packets / window_len
        if "byte_rate" in self.enabled: feat["byte_rate"] = total_bytes / window_len

        if "syn_count" in self.enabled: feat["syn_count"] = tcp_flags_global["syn"]
        if "fin_count" in self.enabled: feat["fin_count"] = tcp_flags_global["fin"]
        if "rst_count" in self.enabled: feat["rst_count"] = tcp_flags_global["rst"]
        if "ack_count" in self.enabled: feat["ack_count"] = tcp_flags_global["ack"]
        if "psh_count" in self.enabled: feat["psh_count"] = tcp_flags_global["psh"]
        if "urg_count" in self.enabled: feat["urg_count"] = tcp_flags_global["urg"]

        if "syn_ratio" in self.enabled: feat["syn_ratio"] = tcp_flags_global["syn"] / total_pkts
        if "fin_ratio" in self.enabled: feat["fin_ratio"] = tcp_flags_global["fin"] / total_pkts
        if "xmas_total" in self.enabled: feat["xmas_total"] = tcp_flags_global["xmas"]
        if "null_scan_total" in self.enabled: feat["null_scan_total"] = tcp_flags_global["null"]

        if "unique_dst_ports" in self.enabled: feat["unique_dst_ports"] = len(dst_port_counts)
        if "unique_src_ports" in self.enabled: feat["unique_src_ports"] = len(src_port_counts)
        if "port_entropy_dst" in self.enabled: feat["port_entropy_dst"] = entropy(dst_port_counts)
        if "port_entropy_src" in self.enabled: feat["port_entropy_src"] = entropy(src_port_counts)

        if all_sizes:
            if "avg_pkt_size" in self.enabled: feat["avg_pkt_size"] = mean(all_sizes)
            if "min_pkt_size" in self.enabled: feat["min_pkt_size"] = min(all_sizes)
            if "max_pkt_size" in self.enabled: feat["max_pkt_size"] = max(all_sizes)
            if "std_pkt_size" in self.enabled: feat["std_pkt_size"] = pstdev(all_sizes)
        else:
            for k in ["avg_pkt_size", "min_pkt_size", "max_pkt_size", "std_pkt_size"]:
                if k in self.enabled: feat[k] = 0

        if "avg_packets_per_flow" in self.enabled:
            feat["avg_packets_per_flow"] = total_packets / total_flows if total_flows else 0
        if "avg_bytes_per_packet" in self.enabled:
            feat["avg_bytes_per_packet"] = total_bytes / total_pkts

        if "proto_tcp_ratio" in self.enabled: feat["proto_tcp_ratio"] = proto_tcp / total_pkts
        if "proto_udp_ratio" in self.enabled: feat["proto_udp_ratio"] = proto_udp / total_pkts
        if "proto_icmp_ratio" in self.enabled: feat["proto_icmp_ratio"] = proto_icmp / total_pkts

        return feat


FEATURE_LIST = [
    "flow_count",
    "total_packets",
    "total_bytes",
    "avg_bytes_per_flow",
    "pkt_rate",
    "byte_rate",

    "syn_count",
    "fin_count",
    "rst_count",
    "ack_count",
    "psh_count",
    "urg_count",
    "syn_ratio",
    "fin_ratio",
    "xmas_total",
    "null_scan_total",

    "unique_dst_ports",
    "unique_src_ports",
    "port_entropy_dst",
    "port_entropy_src",

    "avg_pkt_size",
    "min_pkt_size",
    "max_pkt_size",
    "std_pkt_size",

    "avg_packets_per_flow",
    "avg_bytes_per_packet",
    "proto_tcp_ratio",
    "proto_udp_ratio",
    "proto_icmp_ratio",
]


def entropy(values):
    if not values:
        return 0.0

    total = sum(values.values())
    if total == 0:
        return 0.0

    entropy_val = 0.0
    for count in values.values():
        p = count / total
        entropy_val -= p * math.log2(p)

    return entropy_val
