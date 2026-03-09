# SysInfo4Raspi 🍓

A lightweight Python system monitoring script for Raspberry Pi — no external dependencies, pure Python stdlib.

![Python](https://img.shields.io/badge/python-3.6%2B-blue) ![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **CPU** – clock speed, usage (with progress bar), load average, core count
- **Temperature** – color-coded via `/sys/class/thermal` or `vcgencmd` (green / yellow / red)
- **Memory** – RAM usage with progress bar, buffers & cache
- **Disk** – all mounted partitions with fill level
- **Users** – active SSH sessions including source IP
- **Network** – all interfaces with IP addresses

## Quick Start

Run directly on your Raspberry Pi without downloading first:

```bash
curl -fsSL https://raw.githubusercontent.com/andilar/SysInfo4Raspi/main/sysinfo.py | python3
```

Or download and run locally:

```bash
# Download
curl -fsSL https://raw.githubusercontent.com/andilar/SysInfo4Raspi/main/sysinfo.py -o sysinfo.py

# Run
python3 sysinfo.py
```

Or clone the full repo:

```bash
git clone https://github.com/andilar/SysInfo4Raspi.git
cd SysInfo4Raspi
python3 sysinfo.py
```

## Requirements

- Python 3.6+
- No external packages needed (no `pip install` required)
- Works on all Raspberry Pi models running Raspberry Pi OS / Raspbian

## Color Coding

Thresholds for temperature, CPU, and RAM usage:

| Color  | Meaning         | CPU / RAM | Temperature |
|--------|-----------------|-----------|-------------|
| 🟢 Green  | Normal          | < 60%     | < 60°C      |
| 🟡 Yellow | Warning         | 60–85%    | 60–80°C     |
| 🔴 Red    | Critical        | > 85%     | > 80°C      |

## License

MIT – see [LICENSE](LICENSE)
