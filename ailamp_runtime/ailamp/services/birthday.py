from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import shutil
import subprocess

from ailamp.config import BirthdayConfig
from ailamp.paths import resolve_project_path


@dataclass(frozen=True)
class BirthdayStatus:
    today: date
    enabled: bool
    is_birthday: bool
    already_played: bool
    should_play: bool
    message: str
    motion: str
    rgb: tuple[int, int, int]


class BirthdayService:
    def __init__(self, config: BirthdayConfig):
        self.config = config
        self.state_path = resolve_project_path(config.state_file)

    def status(self, today: date | None = None, *, force: bool = False) -> BirthdayStatus:
        current_date = today or date.today()
        is_birthday = current_date.month == self.config.month and current_date.day == self.config.day
        already_played = self._last_played_date() == current_date.isoformat()
        should_play = self.config.enabled and (force or is_birthday) and (force or not already_played)
        return BirthdayStatus(
            today=current_date,
            enabled=self.config.enabled,
            is_birthday=is_birthday,
            already_played=already_played,
            should_play=should_play,
            message=self.config.message,
            motion=self.config.motion,
            rgb=self.config.rgb,
        )

    def mark_played(self, today: date | None = None) -> None:
        current_date = today or date.today()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({"last_played": current_date.isoformat()}, indent=2) + "\n")

    def speak(self, message: str | None = None) -> str:
        text = message or self.config.message
        command = self._speech_command()
        if command is None:
            return f"speech=unavailable message={text}"
        subprocess.run([command, text], check=False)
        return f"speech={command} message={text}"

    def _last_played_date(self) -> str | None:
        if not self.state_path.exists():
            return None
        try:
            raw = json.loads(self.state_path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        value = raw.get("last_played")
        return value if isinstance(value, str) else None

    def _speech_command(self) -> str | None:
        if self.config.speech_command != "auto":
            return self.config.speech_command
        for candidate in ("say", "spd-say", "espeak"):
            path = shutil.which(candidate)
            if path:
                return path
        return None
