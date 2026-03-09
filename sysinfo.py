#!/usr/bin/env python3
"""
sysinfo.py – Raspberry Pi System Overview
No external dependencies required – pure Python stdlib
"""

import os
import subprocess
import time
from pathlib import Path

# ── Colors ────────────────────────────────────────────────────────────────────
R  = "\033[0;31m"; Y = "\033[1;33m"; G = "\033[0;32m"
C  = "\033[0;36m"; B = "\033[1m";    RST = "\033[0m"

def color(val, warn, crit, fmt="{:.1f}"):
    s = fmt.format(val)
    if val >= crit: return f"{R}{s}{RST}"
    if val >= warn: return f"{Y}{s}{RST}"
    return f"{G}{s}{RST}"

def bar(pct, width=30):
    filled = int(pct * width / 100)
    empty  = width - filled
    return f"[{'█' * filled}{'░' * empty}] {pct:.1f}%"

def section(title):
    print(f"\n{B}{C}── {title} {'─' * (47 - len(title))}{RST}")

def cmd(c):
    try:
        return subprocess.check_output(c, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""

# ── Header ────────────────────────────────────────────────────────────────────
print(f"{B}{C}")
print("╔══════════════════════════════════════════════════╗")
print("║         Raspberry Pi – System Overview           ║")
print(f"╚══════════════════════════════════════════════════╝{RST}")
print(f"  {B}Hostname:{RST}  {cmd('hostname')}   |   {cmd('date \"+%d.%m.%Y %H:%M:%S\"')}")
print(f"  {B}Uptime:{RST}    {cmd('uptime -p')}")

# ── CPU ───────────────────────────────────────────────────────────────────────
section("CPU")

# Clock frequency
freq_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
if freq_path.exists():
    freq_mhz = int(freq_path.read_text().strip()) // 1000
    freq_ghz = freq_mhz / 1000
    print(f"  {B}Clock Speed:{RST}  {freq_mhz} MHz  ({freq_ghz:.2f} GHz)")
else:
    freq = cmd("vcgencmd measure_clock arm 2>/dev/null | awk -F= '{printf \"%.0f\", $2/1000000}'")
    print(f"  {B}Clock Speed:{RST}  {freq or 'n/a'} MHz")

# CPU usage via /proc/stat (no psutil needed)
def cpu_percent(interval=0.5):
    def read():
        line = Path("/proc/stat").read_text().splitlines()[0].split()
        vals = list(map(int, line[1:]))
        idle  = vals[3] + vals[4]  # idle + iowait
        total = sum(vals)
        return idle, total
    i1, t1 = read()
    time.sleep(interval)
    i2, t2 = read()
    return 100.0 * (1 - (i2 - i1) / (t2 - t1))

cpu_use = cpu_percent()
print(f"  {B}Usage:{RST}        {bar(cpu_use)}  ({color(cpu_use, 60, 85, '{:.1f}')}%)")

cores = os.cpu_count()
print(f"  {B}Cores:{RST}        {cores}")

loadavg = Path("/proc/loadavg").read_text().split()[:3]
print(f"  {B}Load (1/5/15m):{RST} {' '.join(loadavg)}")

# ── Temperature ───────────────────────────────────────────────────────────────
section("Temperature")

temp_shown = False
temp_path = Path("/sys/class/thermal/thermal_zone0/temp")
if temp_path.exists():
    temp = int(temp_path.read_text().strip()) / 1000
    print(f"  {B}CPU Temp:{RST}     {color(temp, 60, 80, '{:.1f}')}°C")
    temp_shown = True

vctemp = cmd("vcgencmd measure_temp 2>/dev/null")
if vctemp:
    import re
    m = re.search(r"[\d.]+", vctemp)
    if m:
        temp2 = float(m.group())
        print(f"  {B}GPU Temp:{RST}     {color(temp2, 60, 80, '{:.1f}')}°C  (via vcgencmd)")
        temp_shown = True

if not temp_shown:
    print("  No temperature sensors found.")

# ── RAM ───────────────────────────────────────────────────────────────────────
section("Memory (RAM)")

meminfo = {}
for line in Path("/proc/meminfo").read_text().splitlines():
    parts = line.split()
    if len(parts) >= 2:
        meminfo[parts[0].rstrip(":")] = int(parts[1])

total_mb   = meminfo.get("MemTotal", 0)     // 1024
avail_mb   = meminfo.get("MemAvailable", 0) // 1024
buffers_mb = meminfo.get("Buffers", 0)      // 1024
cached_mb  = (meminfo.get("Cached", 0) + meminfo.get("SReclaimable", 0)) // 1024
used_mb    = total_mb - avail_mb
ram_pct    = used_mb * 100 / total_mb if total_mb else 0

print(f"  {B}Usage:{RST}        {bar(ram_pct)}")
print(f"  {B}Total:{RST}        {total_mb} MB")
print(f"  {B}Used:{RST}         {color(ram_pct, 70, 90, '{:.0f}')} MB  ({used_mb} MB)")
print(f"  {B}Available:{RST}    {avail_mb} MB")
print(f"  {B}Buffers/Cache:{RST} {buffers_mb + cached_mb} MB")

# ── Disk ──────────────────────────────────────────────────────────────────────
section("Disk Usage")

skip = {"tmpfs", "devtmpfs", "overlay", "udev"}
for line in cmd("df -h").splitlines()[1:]:
    parts = line.split()
    if len(parts) < 6:
        continue
    fs, size, used, avail, pct_str, mp = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
    if any(fs.startswith(s) for s in skip):
        continue
    pct = int(pct_str.replace("%", ""))
    col = R if pct >= 90 else (Y if pct >= 75 else G)
    print(f"  {mp:<18} {used}/{size}  {col}{pct_str}{RST}")

# ── Connected Users ───────────────────────────────────────────────────────────
section("Connected Users")

who_out = cmd("who").splitlines()
if who_out:
    print(f"  {B}Active Sessions:{RST} {len(who_out)}")
    for line in who_out:
        parts = line.split()
        user  = parts[0] if len(parts) > 0 else "?"
        tty   = parts[1] if len(parts) > 1 else "?"
        date  = parts[2] if len(parts) > 2 else ""
        ttime = parts[3] if len(parts) > 3 else ""
        host  = parts[4].strip("()") if len(parts) > 4 else ""
        host_info = f"from {host}" if host else ""
        print(f"  • {G}{user}{RST} @ {tty}  {date} {ttime}  {host_info}")
else:
    print("  No active users (local session only).")

# ── Network ───────────────────────────────────────────────────────────────────
section("Network")

for line in cmd("ip -br addr show").splitlines():
    parts = line.split()
    if not parts or parts[0] == "lo":
        continue
    iface = parts[0]
    state = parts[1] if len(parts) > 1 else "?"
    addrs = " ".join(parts[2:]) if len(parts) > 2 else "no IP"
    print(f"  {B}{iface:<12}{RST} {state:<10} {addrs}")

print(f"\n{C}{'─' * 50}{RST}\n")
