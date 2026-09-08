"""PySide6 application window for editing Usage Monitor profiles."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .storage import LoadedProfile, Profile, SettingsError, default_profiles, load_settings, save_settings


DEFAULT_BAR = "#4A9EFF"
DEFAULT_LIGHT = "#FFFFFF"
DEFAULT_DARK = "#000000"


def color_from_rgba(value: Any, fallback: str) -> str:
    """Convert a validated-ish RGBA list to a hex color for the UI."""
    if isinstance(value, list) and len(value) >= 3 and all(isinstance(v, int) for v in value[:3]):
        if all(0 <= v <= 255 for v in value[:3]):
            return "#{:02X}{:02X}{:02X}".format(*value[:3])
    return fallback


def rgba_from_hex(value: str, alpha: int = 255) -> list[int]:
    """Convert a six-digit hex value into the monitor's RGBA representation."""
    color = QColor(value)
    return [color.red(), color.green(), color.blue(), alpha]


def normalize_hex(value: str) -> str:
    """Return a canonical six-digit hex value or raise ``ValueError``."""
    color = QColor(value.strip())
    if not color.isValid() or not value.strip().startswith("#") or len(value.strip()) not in (4, 7):
        raise ValueError("Usa un colore esadecimale come #D97757.")
    return color.name(QColor.HexRgb).upper()


class ColorButton(QPushButton):
    """A compact color swatch that also accepts a color dialog."""

    colorChanged = Signal(str)

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setMinimumWidth(150)
        self.clicked.connect(self.choose_color)
        self._refresh()

    @property
    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        self._color = normalize_hex(color)
        self._refresh()

    def choose_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self._color), self, "Scegli colore")
        if selected.isValid():
            self.set_color(selected.name(QColor.HexRgb))
            self.colorChanged.emit(self._color)

    def _refresh(self) -> None:
        self.setText(self._color)
        color = QColor(self._color)
        luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue())
        text_color = "#111111" if luminance > 150 else "#FFFFFF"
        self.setStyleSheet(
            "QPushButton {"
            f"background-color: {self._color}; color: {text_color};"
            "border: 1px solid #888; border-radius: 4px; padding: 5px;"
            "}"
        )


class PreviewSwatch(QFrame):
    """Small visual preview for one color channel."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignCenter)
        self.swatch = QLabel("Icona")
        self.swatch.setAlignment(Qt.AlignCenter)
        self.swatch.setMinimumHeight(42)
        layout.addWidget(self.title)
        layout.addWidget(self.swatch)

    def set_color(self, color: str, background: str) -> None:
        self.swatch.setStyleSheet(
            f"background-color: {background}; color: {color};"
            "border: 1px solid #777; border-radius: 5px; font-weight: bold;"
        )


class MainWindow(QMainWindow):
    """Main profile editor window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Usage Monitor Config Editor")
        self.resize(980, 680)

        self.profiles: list[Profile] = default_profiles()
        self.loaded: dict[str, LoadedProfile] = {}
        self.modified: set[str] = set()
        self.current_key: str | None = None
        self.command_was_list = False
        self._loading = False

        self._build_ui()
        self._load_profiles()
        if self.profiles:
            self.profile_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        title = QLabel("Profili")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        left_layout.addWidget(title)
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._profile_changed)
        left_layout.addWidget(self.profile_list, 1)
        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #777777;")
        left_layout.addWidget(self.path_label)
        left_buttons = QHBoxLayout()
        self.reload_button = QPushButton("Ricarica")
        self.open_button = QPushButton("Apri cartella")
        self.reload_button.clicked.connect(self._reload_current)
        self.open_button.clicked.connect(self._open_current_folder)
        left_buttons.addWidget(self.reload_button)
        left_buttons.addWidget(self.open_button)
        left_layout.addLayout(left_buttons)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.profile_title = QLabel("Nessun profilo")
        self.profile_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        right_layout.addWidget(self.profile_title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_colors_tab(), "Aspetto")
        self.tabs.addTab(self._build_command_tab(), "Quick action")
        self.tabs.addTab(self._build_json_tab(), "JSON")
        right_layout.addWidget(self.tabs, 1)

        action_row = QHBoxLayout()
        self.status_label = QLabel("Pronto")
        self.status_label.setStyleSheet("color: #777777;")
        action_row.addWidget(self.status_label, 1)
        self.save_button = QPushButton("Salva profilo")
        self.save_all_button = QPushButton("Salva tutti")
        self.save_button.clicked.connect(self._save_current)
        self.save_all_button.clicked.connect(self._save_all)
        action_row.addWidget(self.save_button)
        action_row.addWidget(self.save_all_button)
        right_layout.addLayout(action_row)
        splitter.addWidget(right)
        splitter.setSizes([245, 735])

    def _build_colors_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        explanation = QLabel(
            "I colori vengono salvati come esadecimali per la barra e come RGBA per l'icona. "
            "icon_light è usato su taskbar scura; icon_dark su taskbar chiara."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #666666;")
        layout.addWidget(explanation)

        form_box = QGroupBox("Colori principali")
        form = QFormLayout(form_box)
        self.bar_color = ColorButton(DEFAULT_BAR)
        self.light_color = ColorButton(DEFAULT_LIGHT)
        self.dark_color = ColorButton(DEFAULT_DARK)
        for button in (self.bar_color, self.light_color, self.dark_color):
            button.colorChanged.connect(self._mark_dirty)
        form.addRow("Barra di utilizzo", self.bar_color)
        form.addRow("Icona taskbar scura", self.light_color)
        form.addRow("Icona taskbar chiara", self.dark_color)
        layout.addWidget(form_box)

        preview_box = QGroupBox("Anteprima")
        preview_layout = QHBoxLayout(preview_box)
        self.preview_light = PreviewSwatch("Taskbar scura")
        self.preview_dark = PreviewSwatch("Taskbar chiara")
        self.preview_bar = PreviewSwatch("Barra")
        preview_layout.addWidget(self.preview_light)
        preview_layout.addWidget(self.preview_dark)
        preview_layout.addWidget(self.preview_bar)
        layout.addWidget(preview_box)
        layout.addStretch()
        return tab

    def _build_command_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        box = QGroupBox("Comando quick action")
        form = QFormLayout(box)
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("Esempio: explorer.exe shell:AppsFolder\\...")
        self.command_edit.textChanged.connect(self._mark_dirty)
        form.addRow("Comando", self.command_edit)
        path_hint = QLabel(
            "Il comando viene eseguito quando attivi il quick action dal monitor. "
            "È un comando shell: usa soltanto comandi di cui ti fidi."
        )
        path_hint.setWordWrap(True)
        path_hint.setStyleSheet("color: #666666;")
        form.addRow("Nota", path_hint)
        layout.addWidget(box)
        test_row = QHBoxLayout()
        self.test_command_button = QPushButton("Testa comando")
        self.test_command_button.clicked.connect(self._test_command)
        test_row.addWidget(self.test_command_button)
        test_row.addStretch()
        layout.addLayout(test_row)
        layout.addStretch()
        return tab

    def _build_json_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        note = QLabel("Anteprima del JSON in memoria. Il salvataggio mantiene anche le chiavi non gestite dall'editor.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #666666;")
        layout.addWidget(note)
        self.json_view = QPlainTextEdit()
        self.json_view.setReadOnly(True)
        self.json_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.json_view)
        return tab

    def _load_profiles(self) -> None:
        self.profile_list.clear()
        for profile in self.profiles:
            loaded = load_settings(profile)
            self.loaded[profile.key] = loaded
            item = QListWidgetItem(profile.label)
            item.setData(Qt.UserRole, profile.key)
            self.profile_list.addItem(item)
            self._refresh_item(item, loaded)

    def _refresh_item(self, item: QListWidgetItem, loaded: LoadedProfile) -> None:
        if loaded.error:
            item.setText(f"{loaded.profile.label}  — errore")
            item.setToolTip(loaded.error)
        elif loaded.exists:
            marker = " *" if loaded.profile.key in self.modified else ""
            item.setText(f"{loaded.profile.label}{marker}")
            item.setToolTip(str(loaded.profile.path))
        else:
            item.setText(f"{loaded.profile.label}  — nuovo")
            item.setToolTip(f"Verrà creato: {loaded.profile.path}")

    def _profile_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if previous is not None:
            self._capture_editor()
        if current is None:
            return
        self.current_key = current.data(Qt.UserRole)
        loaded = self.loaded[self.current_key]
        self.profile_title.setText(loaded.profile.label)
        self.path_label.setText(str(loaded.profile.path))
        self.path_label.setToolTip(str(loaded.profile.path))
        self._populate_editor(loaded.data)
        self.status_label.setText(loaded.error or ("File presente" if loaded.exists else "File non ancora creato"))

    def _populate_editor(self, data: dict[str, Any]) -> None:
        self._loading = True
        try:
            self.bar_color.set_color(data.get("bar_fg", DEFAULT_BAR))
            light = data.get("icon_light", {})
            dark = data.get("icon_dark", {})
            self.light_color.set_color(color_from_rgba(light.get("fg"), DEFAULT_LIGHT))
            self.dark_color.set_color(color_from_rgba(dark.get("fg"), DEFAULT_DARK))

            command = data.get("quick_action_command", "")
            self.command_was_list = isinstance(command, list)
            if isinstance(command, list):
                self.command_edit.setText(" ".join(str(part) for part in command))
            else:
                self.command_edit.setText(str(command))
        finally:
            self._loading = False

        self._refresh_preview()
        self.json_view.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))

    def _capture_editor(self) -> None:
        if not self.current_key or self.current_key not in self.loaded:
            return
        original = self.loaded[self.current_key].data
        data = copy.deepcopy(original)
        data["bar_fg"] = normalize_hex(self.bar_color.color)
        data["icon_light"] = self._updated_icon(data.get("icon_light", {}), self.light_color.color)
        data["icon_dark"] = self._updated_icon(data.get("icon_dark", {}), self.dark_color.color)
        command = self.command_edit.text().strip()
        if self.command_was_list:
            original_command = original.get("quick_action_command")
            if isinstance(original_command, list) and command == " ".join(str(part) for part in original_command):
                data["quick_action_command"] = copy.deepcopy(original_command)
            else:
                data["quick_action_command"] = command
        else:
            data["quick_action_command"] = command
        self.loaded[self.current_key].data = data
        self._refresh_preview()
        self.json_view.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))

    @staticmethod
    def _updated_icon(existing: Any, color: str) -> dict[str, list[int]]:
        section = copy.deepcopy(existing) if isinstance(existing, dict) else {}
        old_half = section.get("fg_half", [0, 0, 0, 80])
        old_dim = section.get("fg_dim", [0, 0, 0, 140])
        half_alpha = old_half[3] if isinstance(old_half, list) and len(old_half) == 4 else 80
        dim_alpha = old_dim[3] if isinstance(old_dim, list) and len(old_dim) == 4 else 140
        section["fg"] = rgba_from_hex(color, 255)
        section["fg_half"] = rgba_from_hex(color, half_alpha)
        section["fg_dim"] = rgba_from_hex(color, dim_alpha)
        return section

    def _mark_dirty(self, *_args: Any) -> None:
        if self.current_key and not self._loading:
            self.modified.add(self.current_key)
            item = self.profile_list.currentItem()
            if item:
                self._refresh_item(item, self.loaded[self.current_key])
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        self.preview_light.set_color(self.light_color.color, "#202020")
        self.preview_dark.set_color(self.dark_color.color, "#F2F2F2")
        self.preview_bar.set_color("#FFFFFF", self.bar_color.color)

    def _save_current(self) -> bool:
        if not self.current_key:
            return False
        self._capture_editor()
        return self._save_key(self.current_key)

    def _save_all(self) -> None:
        if self.current_key:
            self._capture_editor()
        success = True
        for key in list(self.modified):
            success = self._save_key(key) and success
        if success:
            self.status_label.setText("Tutti i profili modificati sono stati salvati.")

    def _save_key(self, key: str) -> bool:
        loaded = self.loaded[key]
        try:
            path = save_settings(loaded.profile, loaded.data)
        except (OSError, SettingsError, TypeError, ValueError) as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return False
        loaded.exists = True
        loaded.error = ""
        self.modified.discard(key)
        row = next((i for i in range(self.profile_list.count()) if self.profile_list.item(i).data(Qt.UserRole) == key), None)
        if row is not None:
            self._refresh_item(self.profile_list.item(row), loaded)
        if key == self.current_key:
            self.status_label.setText(f"Salvato: {path} (backup .bak creato se esisteva)")
            self.json_view.setPlainText(json.dumps(loaded.data, ensure_ascii=False, indent=2))
        return True

    def _reload_current(self) -> None:
        if not self.current_key:
            return
        loaded = load_settings(self.loaded[self.current_key].profile)
        self.loaded[self.current_key] = loaded
        self.modified.discard(self.current_key)
        self._populate_editor(loaded.data)
        self.status_label.setText(loaded.error or "Ricaricato dal disco")
        item = self.profile_list.currentItem()
        if item:
            self._refresh_item(item, loaded)

    def _open_current_folder(self) -> None:
        if not self.current_key:
            return
        folder = self.loaded[self.current_key].profile.directory
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)  # type: ignore[attr-defined]

    def _test_command(self) -> None:
        command = self.command_edit.text().strip()
        if not command:
            QMessageBox.information(self, "Quick action", "Non è configurato alcun comando.")
            return
        answer = QMessageBox.question(
            self,
            "Conferma esecuzione",
            f"Eseguire questo comando?\n\n{command}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            subprocess.Popen(command, shell=True, cwd=str(Path.home()))
            self.status_label.setText("Comando avviato.")
        except OSError as exc:
            QMessageBox.critical(self, "Quick action", str(exc))


def run() -> int:
    """Start the editor application."""
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Usage Monitor Config Editor")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()
