from datetime import date

from ailamp.config import BirthdayConfig
from ailamp.services.birthday import BirthdayService


def birthday_config(state_file: str) -> BirthdayConfig:
    return BirthdayConfig(
        enabled=True,
        month=5,
        day=8,
        message="Happy birthday, Yugu!",
        motion="happy_wiggle",
        rgb=(255, 180, 80),
        state_file=state_file,
        speech_command="auto",
    )


def test_birthday_triggers_on_configured_day(tmp_path, monkeypatch):
    monkeypatch.setenv("AILAMP_PROJECT_ROOT", str(tmp_path))
    service = BirthdayService(birthday_config("birthday_state.json"))

    status = service.status(date(2026, 5, 8))

    assert status.is_birthday
    assert status.should_play
    assert status.message == "Happy birthday, Yugu!"
    assert status.motion == "happy_wiggle"
    assert status.rgb == (255, 180, 80)


def test_birthday_does_not_repeat_after_marking_played(tmp_path, monkeypatch):
    monkeypatch.setenv("AILAMP_PROJECT_ROOT", str(tmp_path))
    service = BirthdayService(birthday_config("birthday_state.json"))

    service.mark_played(date(2026, 5, 8))
    status = service.status(date(2026, 5, 8))

    assert status.already_played
    assert not status.should_play


def test_birthday_force_ignores_date_and_state(tmp_path, monkeypatch):
    monkeypatch.setenv("AILAMP_PROJECT_ROOT", str(tmp_path))
    service = BirthdayService(birthday_config("birthday_state.json"))
    service.mark_played(date(2026, 5, 8))

    status = service.status(date(2026, 5, 8), force=True)

    assert status.should_play
