from __future__ import annotations

import html
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template


app = Flask(__name__)


SERVICES = [
    "pi-dashboard.service",
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
    output = run_cmd(
            ["systemctl",
             "list-timers",
             "--all",
             "--no-pager",
             "--no-legend",
             ]
            )
    for line in output.splitlines():
        if "soundcloud-notifier.timer" in line:
            return line

    return "soundcloud-notifier.timer was not found in systemctl list-timers."


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

def colorize_logs(log_text: str) -> str:
    colored_lines = []

    for line in log_text.splitlines():
        escaped_line = html.escape(line)
        lower_line = line.lower()

        if any(word in lower_line for word in ["error", "failed", "traceback", "exception", "login_required", "checkpoint", "challenge"]):
            css_class = "log-error"
        elif any(word in lower_line for word in ["warning", "skipping", "already seen", "no matching"]):
            css_class = "log-warning"
        elif any(word in lower_line for word in ["searching", "config loaded", "starting"]):
            css_class = "log-info"
        elif any(word in lower_line for word in ["success", "unfinished", "deactivated successfully", "new track", "new story"]):
            css_class = "log-success"
        else:
            css_class = "log-normal"

        colored_lines.append(f'<span class="{css_class}">{escaped_line}</span>')
    return "\n".join(colored_lines)

@app.route("/")
def index():
    services = [get_service_status(unit) for unit in SERVICES]
    logs = {unit: colorize_logs(get_logs(unit)) for unit in LOG_UNITS}

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


