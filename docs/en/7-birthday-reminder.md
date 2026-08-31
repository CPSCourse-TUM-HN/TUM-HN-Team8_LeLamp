# 7. Birthday Reminder

AILamp does not use a hidden backdoor. The birthday reminder is an explicit configuration block in `config/hardware.toml`:

```toml
[birthday]
enabled = true
month = 5
day = 8
message = "Happy birthday, Yugu!"
motion = "happy_wiggle"
rgb = [255, 180, 80]
state_file = "outputs/birthday_state.json"
speech_command = "auto"
```

Local test:

```bash
ailamp birthday-check --today 2026-05-08 --dry-run
ailamp birthday-check --today 2026-05-08 --force --speak
```

Jetson automatic run:

```bash
sudo cp deploy/systemd/ailamp-birthday.service /etc/systemd/system/
sudo cp deploy/systemd/ailamp-birthday.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ailamp-birthday.timer
```

Before deploying, edit `/opt/AILamp` in the service file to the real project path. The timer runs daily; the CLI only triggers on the configured date and uses `state_file` to avoid replaying on the same day.
