#!/usr/bin/env python3
"""GigaAM Transcriber — голосовой ввод через системный трей."""

import io
import logging
import signal
import subprocess
import sys
import tempfile
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

import gigaam
import numpy as np
import pyperclip
import sounddevice as sd
from PIL import Image, ImageDraw
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from scipy.io import wavfile

# Платформа
IS_MAC = sys.platform == "darwin"

# Логирование
if IS_MAC:
    LOG_DIR = Path.home() / "Library/Application Support/gigaam-transcriber"
else:
    LOG_DIR = Path.home() / ".local/share/gigaam-transcriber"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        RotatingFileHandler(LOG_DIR / "transcriber.log", maxBytes=5_000_000, backupCount=2),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__).info

# Константы
SAMPLE_RATE = 16000
CHUNK_SECONDS = 20


def create_icon(color: str) -> Image.Image:
    """Создаёт иконку микрофона."""
    colors = {"green": "#4CAF50", "red": "#F44336", "yellow": "#FFC107", "gray": "#9E9E9E"}
    fill = colors.get(color, colors["green"])

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([20, 8, 44, 40], fill=fill)
    draw.rectangle([20, 24, 44, 40], fill=fill)
    draw.arc([16, 28, 48, 52], start=0, end=180, fill=fill, width=4)
    draw.line([32, 52, 32, 58], fill=fill, width=4)
    draw.line([22, 58, 42, 58], fill=fill, width=4)
    return img


def paste_text(text: str) -> None:
    """Вставляет текст через буфер обмена."""
    old_clipboard = pyperclip.paste()
    pyperclip.copy(text)
    time.sleep(0.1)

    if IS_MAC:
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to keystroke "v" using command down'
        ], timeout=2)
    else:
        result = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=1)
        if result.returncode == 0:
            subprocess.run(["xdotool", "key", "--window", result.stdout.strip(), "ctrl+v"], timeout=2)

    time.sleep(0.3)
    pyperclip.copy(old_clipboard)
    log(f"✓ Вставлено: {len(text)} символов")


class Transcriber:
    """Основной класс транскрибера."""

    def __init__(self):
        self.model = None
        self.stream = None
        self.recording = False
        self.audio_data = []

    def load_model(self) -> bool:
        log("Загрузка GigaAM v3...")
        self.model = gigaam.load_model("v3_e2e_rnnt")
        log("✓ Модель загружена")
        return True

    def start_recording(self) -> bool:
        if not self.model:
            log("✗ Модель не загружена")
            return False

        self.audio_data = []
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self.stream.start()
        self.recording = True
        log("● Запись...")
        return True

    def stop_recording(self) -> np.ndarray | None:
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_data:
            return None
        return np.concatenate(self.audio_data).flatten()

    def transcribe(self, audio: np.ndarray) -> str:
        duration = len(audio) / SAMPLE_RATE
        log(f"Обработка {duration:.1f}с...")
        start = time.time()

        if duration <= CHUNK_SECONDS:
            text = self._transcribe_audio(audio)
        else:
            text = self._transcribe_chunks(audio)

        log(f"✓ Готово за {time.time() - start:.1f}с: {len(text)} символов")
        return text

    def _transcribe_audio(self, audio: np.ndarray) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = Path(f.name)
            wavfile.write(path, SAMPLE_RATE, (audio * 32767).astype(np.int16))
        text = self.model.transcribe(str(path)) or ""
        path.unlink(missing_ok=True)
        return text

    def _transcribe_chunks(self, audio: np.ndarray) -> str:
        chunk_samples = CHUNK_SECONDS * SAMPLE_RATE
        num_chunks = int(np.ceil(len(audio) / chunk_samples))

        parts = []
        for i in range(num_chunks):
            chunk = audio[i * chunk_samples : (i + 1) * chunk_samples]
            text = self._transcribe_audio(chunk)
            if text.strip():
                parts.append(text)
                log(f"  Чанк {i + 1}/{num_chunks}: {len(text)} символов")

        return " ".join(parts)

    def _audio_callback(self, indata, _frames, _time_info, _status):
        if self.recording:
            self.audio_data.append(indata.copy())


class TrayApp:
    """Приложение в системном трее."""

    def __init__(self, transcriber: Transcriber):
        self.transcriber = transcriber
        self.app = QApplication(sys.argv)
        self.tray = QSystemTrayIcon()

        menu = QMenu()
        exit_action = QAction("Выход")
        exit_action.triggered.connect(self._quit)
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_click)
        self._set_icon("gray", "Загрузка...")
        self.tray.show()

    def _set_icon(self, color: str, tooltip: str):
        buf = io.BytesIO()
        create_icon(color).save(buf, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        self.tray.setIcon(QIcon(pixmap))
        self.tray.setToolTip(tooltip)

    def _on_click(self, reason):
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return

        if self.transcriber.recording:
            self._set_icon("yellow", "Обработка...")
            threading.Thread(target=self._process, daemon=True).start()
        elif self.transcriber.start_recording():
            self._set_icon("red", "Запись...")

    def _process(self):
        audio = self.transcriber.stop_recording()
        if audio is not None:
            text = self.transcriber.transcribe(audio)
            if text.strip():
                paste_text(text)
        self._set_icon("green", "GigaAM Transcriber")

    def _quit(self):
        self.transcriber.stop_recording()
        self.app.quit()

    def run(self):
        self.app.exec()


def main():
    log("=" * 40)
    log("GigaAM Transcriber v3")
    log("=" * 40)

    transcriber = Transcriber()
    app = TrayApp(transcriber)

    signal.signal(signal.SIGINT, lambda *_: app._quit())
    signal.signal(signal.SIGTERM, lambda *_: app._quit())

    threading.Thread(
        target=lambda: (transcriber.load_model(), app._set_icon("green", "GigaAM Transcriber")),
        daemon=True,
    ).start()

    app.run()


if __name__ == "__main__":
    main()
