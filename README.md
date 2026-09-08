# Usage Monitor Config Editor

Visual Windows editor for the `usage-monitor-settings.json` profiles used by
the Usage Monitor family of applications.

## Current scope

The application starts with an empty profile list. Use **Aggiungi profilo** to
select any JSON configuration file and give it a display name. The selected
list is remembered between runs in:

```text
%LOCALAPPDATA%\UsageMonitorConfigEditor\profiles.json
```

Removing a profile only removes it from this list; the original JSON file is
never deleted. This makes it possible to manage the Claude, Claude Valeria,
Codex and Copilot files, as well as additional profiles, without changing the
application code.

It provides:

- Visual color editing for the popup bar and tray icon themes.
- Quick action command editing and an explicit test button.
- Selectable profile list with persistent local history.
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
