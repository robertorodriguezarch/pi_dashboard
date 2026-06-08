from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template


app = Flask(__name__)


SERVICES = [
    "ig-story-bot.service",
    "soundcloud-notifier.timer",
    "soundcloud-notifier.service",
    "tailscaled.service",
    "ssh.service",
]


LOG_UNITS = [
    "ig-story-bot.service",
    "soundcloud-notifier.service",
]

def run_cmd(command: list[str]) -> str:
    try:
        result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output
    except Exception as exc:
        return f"Error running command: {exc}"

def get_uptime() -> str:
    return run_cmd(["uptime", "-p"])

def get_cpu_temp() -> str:
    temp_path = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        raw = temp_path.read_text().strip()
        celsius = int(raw) / 1000
        return f"{celsius:.1f}°C"
    except Exception:
        return "Unknown"

def get_memory() -> str:
    output = run_cmd(["free", "-h"])
    lines = output.splitlines()
    if len(lines) >= 2:
        return lines[1]
    return output

def get_disk() -> str:
    total, used, free = shutil.disk_usage("/")
    return (
        f"{used / (1024**3):.1f} GB used / "
        f"{total / (1024**3):.1f} GB total "
        f"({free / (1024**3):.1f} GB free)"
    )

def get_service_status(unit: str) -> dict[str, str]:
    active = run_cmd(["systemctl", "is-active", unit])
    enabled = run_cmd(["systemctl", "is-enabled", unit])
    return {
        "name": unit,
        "active": active,
        "enabled": enabled,
    }

def get_timer_info() -> str:
    return run_cmd(["systemctl", "list-timers", "--all", "soundcloud-notifer.timer"])


def get_logs(unit: str, lines: int = 25) -> str:
    return run_cmd(
        [
            "journalctl",
            "-u",
            unit,
            "-n",
            str(lines),
            "--no-pager",
            "-o",
            "short",
        ]
    )


@app.route("/")
def index():
    services = [get_service_status(unit) for unit in SERVICES]
    logs = {unit: get_logs(unit) for unit in LOG_UNITS}

    return render_template(
            "index.html",
            now=datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            uptime=get_uptime(),
            cpu_temp=get_cpu_temp(),
            memory=get_memory(),
            disk=get_disk(),
            services=services,
            timer_info=get_timer_info(),
            logs=logs,
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)


