# streamml

Streamml processes network packets in real-time, feeding them into the Half-Space Trees algorithm (via the [River](https://riverml.xyz/dev/api/anomaly/HalfSpaceTrees/) library). When the score exceeds the defined threshold, the application saves an evidentiary PCAP dump containing the relevant packet window.

Note: Currently supports Half-Space Trees, with plans to add more algorithms.

### Prerequisites
Ensure you have [uv](https://github.com/astral-sh/uv) installed.

### Running

Root privileges are needed for packet sniffing.
```bash
sudo uv run -m streamml.app
```


### Results are stored here:

LOGS_PATH = XDG_DATA_HOME/streamml/profiles_logs

PCAP_PATH = XDG_DATA_HOME/streamml/profiles_pcaps


### This is how it works:

                  +--------------------+
                  | Profile Activation |
                  +---------+----------+
                            |
            +---------------+---------------+
            |                               |
    +-------v-------+               +-------v---------+
    | Start Sniffer |               | Start Processor |
    +-------+-------+               +-------+---------+                           
            |                               |                                     
    +-------v-------+               +-------v-------------+                       
    |   BPF Filter  |               | Get Packet from     |<------+
    +-------+-------+               | FIFO                |       |
            |                       +-------+-------------+       |
    +-------v-------+                       |                     |
    | Receive Packet|               +-------v-------------+       |
    +-------+-------+               | Add Packet to       |       |
            |                       | Window              |       |
    +-------v-------+               +-------+-------------+       |
    |  Add to FIFO  |                       |                     |
    +---------------+               +-------v-------------+   No  |
                                    |   End of Window?    +-------+
                                    +-------+-------------+       |
                                            | Yes                 |
                                    +-------v-------------+       |
                                    | Calculate Features  |       |
                                    +-------+-------------+       |
                                            |                     |
                                    +-------v-------------+       |
                                    | HST: score_one +    |       |
                                    | learn_one           |       |
                                    +-------+-------------+       |
                                            |                     |
                                    +-------v-------------+   No  |
                                    | Score > Threshold?  +-------+
                                    +-------+-------------+
                                            | Yes
                                    +-------v-------------+
                                    | PCAP Save           |
                                    | Logging             |
                                    | Alert               |
                                    +---------------------+

### Screenshots
<img width="988" height="540" alt="screenshot1" src="https://github.com/user-attachments/assets/65ed2870-fb2c-4212-9db6-d74b10248809" />

