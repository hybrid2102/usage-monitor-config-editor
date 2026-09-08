# Usage Monitor Config Editor

Visual Windows editor for the `usage-monitor-settings.json` profiles used by
the Usage Monitor family of applications.

## Current scope

The first version manages these profiles automatically:

- `%USERPROFILE%\.claude\usage-monitor-settings.json`
- `%USERPROFILE%\.claude-valeria\usage-monitor-settings.json`
- `%USERPROFILE%\.codex\usage-monitor-settings.json`
- `%USERPROFILE%\.copilot\usage-monitor-settings.json`

It provides:

- Visual color editing for the popup bar and tray icon themes.
- Quick action command editing and an explicit test button.
- Read-only JSON preview that preserves settings the editor does not manage.
- Atomic saves and a `.bak` backup of the previous file.
- Support for profiles that do not exist yet.

## Run from source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m config_editor
```

## Build the Windows executable

```powershell
python build.py
```

The executable is created at `dist\UsageMonitorConfigEditor.exe`.

## Safety notes

The editor does not start, stop or restart the monitor automatically. After
saving, restart the relevant monitor instance from its tray menu. The test
button asks for confirmation because quick action values are shell commands.

