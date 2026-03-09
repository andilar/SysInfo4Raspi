#!/usr/bin/env python3
"""
sysinfo.py – Raspberry Pi System Overview
No external dependencies required – pure Python stdlib

Usage:
  python3 sysinfo.py           # single run
  python3 sysinfo.py --live    # live mode (refreshes every 2s)
  python3 sysinfo.py --live 5  # live mode with custom interval (seconds)
"""

import os
import re
import sys
import subprocess
import time
from pathlib import Path

# ── Args ──────────────────────────────────────────────────────────────────────
args      = sys.argv[1:]
LIVE_MODE = "--live" in args
INTERVAL  = 2
if LIVE_MODE:
    idx = args.index("--live")
    if idx + 1 < len(args):
        try:
            INTERVAL = int(args[idx + 1])
        except ValueError:
            pass

# ── Colors ────────────────────────────────────────────────────────────────────
R   = "\033[0;31m"; Y = "\033[1;33m"; G = "\033[0;32m"
C   = "\033[0;36m"; B = "\033[1m";    RST = "\033[0m"
CLR = "\033[2J\033[H"  # clear screen + move cursor to top

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
    _out(f"\n{B}{C}── {title} {'─' * (47 - len(title))}{RST}")

def cmd(c):
    try:
        return subprocess.check_output(c, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""

# Buffer output so screen clears only when ready (avoids flicker)
_buf = []
def _out(s=""): _buf.append(s)
def _flush():
    if LIVE_MODE:
        print(CLR, end="")
    print("\n".join(_buf))
    _buf.clear()

# ── CPU helper ────────────────────────────────────────────────────────────────
def cpu_percent(interval=0.5):
    def read():
        line = Path("/proc/stat").read_text().splitlines()[0].split()
        vals = list(map(int, line[1:]))
        return vals[3] + vals[4], sum(vals)  # idle, total
    i1, t1 = read()
    time.sleep(interval)
    i2, t2 = read()
    return 100.0 * (1 - (i2 - i1) / (t2 - t1))

# ── Main render ───────────────────────────────────────────────────────────────
def render():
    # Header
    _out(f"{B}{C}")
    _out("╔══════════════════════════════════════════════════╗")
    if LIVE_MODE:
        _out("║     Raspberry Pi – Live Monitor  (Ctrl+C)        ║")
    else:
        _out("║         Raspberry Pi – System Overview           ║")
    _out(f"╚══════════════════════════════════════════════════╝{RST}")
    date_str = cmd('date "+%d.%m.%Y %H:%M:%S"')
    _out(f"  {B}Hostname:{RST}  {cmd('hostname')}   |   {date_str}")
    _out(f"  {B}Uptime:{RST}    {cmd('uptime -p')}")
    if LIVE_MODE:
        _out(f"  {B}Refresh:{RST}   every {INTERVAL}s")

    # CPU
    section("CPU")
    freq_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    if freq_path.exists():
        freq_mhz = int(freq_path.read_text().strip()) // 1000
        _out(f"  {B}Clock Speed:{RST}  {freq_mhz} MHz  ({freq_mhz / 1000:.2f} GHz)")
    else:
        freq = cmd("vcgencmd measure_clock arm 2>/dev/null | awk -F= '{printf \"%.0f\", $2/1000000}'")
        _out(f"  {B}Clock Speed:{RST}  {freq or 'n/a'} MHz")

    cpu_use = cpu_percent()
    _out(f"  {B}Usage:{RST}        {bar(cpu_use)}  ({color(cpu_use, 60, 85, '{:.1f}')}%)")
    _out(f"  {B}Cores:{RST}        {os.cpu_count()}")
    loadavg = Path("/proc/loadavg").read_text().split()[:3]
    _out(f"  {B}Load (1/5/15m):{RST} {' '.join(loadavg)}")

    # Temperature
    section("Temperature")
    temp_shown = False
    temp_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if temp_path.exists():
        temp = int(temp_path.read_text().strip()) / 1000
        _out(f"  {B}CPU Temp:{RST}     {color(temp, 60, 80, '{:.1f}')}°C")
        temp_shown = True
    vctemp = cmd("vcgencmd measure_temp 2>/dev/null")
    if vctemp:
        m = re.search(r"[\d.]+", vctemp)
        if m:
            _out(f"  {B}GPU Temp:{RST}     {color(float(m.group()), 60, 80, '{:.1f}')}°C  (via vcgencmd)")
            temp_shown = True
    if not temp_shown:
        _out("  No temperature sensors found.")

    # RAM
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
    _out(f"  {B}Usage:{RST}        {bar(ram_pct)}")
    _out(f"  {B}Total:{RST}        {total_mb} MB")
    _out(f"  {B}Used:{RST}         {color(ram_pct, 70, 90, '{:.0f}')} MB  ({used_mb} MB)")
    _out(f"  {B}Available:{RST}    {avail_mb} MB")
    _out(f"  {B}Buffers/Cache:{RST} {buffers_mb + cached_mb} MB")

    # Disk
    section("Disk Usage")
    skip = {"tmpfs", "devtmpfs", "overlay", "udev"}
    for line in cmd("df -h").splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6: continue
        fs, size, used, avail, pct_str, mp = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        if any(fs.startswith(s) for s in skip): continue
        pct = int(pct_str.replace("%", ""))
        col = R if pct >= 90 else (Y if pct >= 75 else G)
        _out(f"  {mp:<18} {used}/{size}  {col}{pct_str}{RST}")

    # Connected Users
    section("Connected Users")
    who_out = cmd("who").splitlines()
    if who_out:
        _out(f"  {B}Active Sessions:{RST} {len(who_out)}")
        for line in who_out:
            parts = line.split()
            user  = parts[0] if len(parts) > 0 else "?"
            tty   = parts[1] if len(parts) > 1 else "?"
            date  = parts[2] if len(parts) > 2 else ""
            ttime = parts[3] if len(parts) > 3 else ""
            host  = parts[4].strip("()") if len(parts) > 4 else ""
            _out(f"  • {G}{user}{RST} @ {tty}  {date} {ttime}  {'from ' + host if host else ''}")
    else:
        _out("  No active users (local session only).")

    # Network
    section("Network")
    for line in cmd("ip -br addr show").splitlines():
        parts = line.split()
        if not parts or parts[0] == "lo": continue
        iface = parts[0]
        state = parts[1] if len(parts) > 1 else "?"
        addrs = " ".join(parts[2:]) if len(parts) > 2 else "no IP"
        _out(f"  {B}{iface:<12}{RST} {state:<10} {addrs}")

    _out(f"\n{C}{'─' * 50}{RST}\n")
    _flush()

# ── Entry point ───────────────────────────────────────────────────────────────
if LIVE_MODE:
    try:
        while True:
            render()
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print(f"\n{Y}Live monitor stopped.{RST}\n")
else:
    render()
