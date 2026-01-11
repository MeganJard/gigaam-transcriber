#!/usr/bin/env python3
"""
GigaAM Transcriber - приложение для голосового ввода текста.
Висит в системном трее, записывает речь и вставляет транскрипцию в место курсора.
"""

import os
import sys
import tempfile
import threading
import time
import signal
import atexit
import subprocess

import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from PIL import Image, ImageDraw
from pynput.keyboard import Controller as KeyboardController, Key, Listener as KeyboardListener, KeyCode
import pyperclip

# Глобальные переменные
model = None
keyboard = KeyboardController()
tray_icon = None
keyboard_listener = None
current_keys = set()
is_recording = False
audio_data = []
audio_stream = None
sample_rate = 16000  # GigaAM требует 16kHz


def create_icon_image(color: str = "green") -> Image.Image:
    """Создаёт иконку для трея."""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    colors = {
        "green": "#4CAF50",
        "red": "#F44336",
        "yellow": "#FFC107",
        "gray": "#9E9E9E",
    }

    fill_color = colors.get(color, colors["green"])

    # Рисуем микрофон
    draw.ellipse([20, 8, 44, 40], fill=fill_color)
    draw.rectangle([20, 24, 44, 40], fill=fill_color)
    draw.arc([16, 28, 48, 52], start=0, end=180, fill=fill_color, width=4)
    draw.line([32, 52, 32, 58], fill=fill_color, width=4)
    draw.line([22, 58, 42, 58], fill=fill_color, width=4)

    return image


def load_model():
    """Загружает модель GigaAM v3 с пунктуацией."""
    global model
    print("Загрузка модели GigaAM v3 (с пунктуацией)...")

    try:
        import gigaam
        # v3 e2e модель с пунктуацией и нормализацией
        model = gigaam.load_model("v3_e2e_rnnt")
        print("Модель загружена успешно!")
        return True
    except Exception as e:
        print(f"Ошибка загрузки модели: {e}")
        # Попробуем fallback на v2
        try:
            print("Пробуем загрузить v2_rnnt...")
            model = gigaam.load_model("v2_rnnt")
            print("Модель v2 загружена (без пунктуации)")
            return True
        except Exception as e2:
            print(f"Ошибка загрузки v2: {e2}")
            return False


def record_audio_callback(indata, frames, time_info, status):
    """Callback для записи аудио."""
    global audio_data
    if is_recording:
        audio_data.append(indata.copy())


def start_recording():
    """Начинает запись аудио."""
    global is_recording, audio_data, audio_stream

    if model is None:
        print("Модель ещё не загружена!")
        return False

    audio_data = []

    # Запускаем аудио-стрим только сейчас
    audio_stream = sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32,
        callback=record_audio_callback,
    )
    audio_stream.start()

    is_recording = True
    print("Запись начата... (Ctrl+Alt+R для остановки)")
    return True


def stop_recording():
    """Останавливает запись."""
    global is_recording, audio_stream

    is_recording = False

    if audio_stream:
        audio_stream.stop()
        audio_stream.close()
        audio_stream = None


def stop_recording_and_transcribe(icon):
    """Останавливает запись и транскрибирует."""
    global audio_data

    stop_recording()
    print("Запись остановлена. Обработка...")

    if not audio_data:
        print("Нет записанных данных")
        if hasattr(icon, 'update_icon'):
            icon.update_icon("green", "GigaAM Transcriber - Ctrl+Alt+R")
        return

    if hasattr(icon, 'update_icon'):
        icon.update_icon("yellow", "GigaAM Transcriber (обработка...)")

    try:
        # Объединяем все записанные данные
        audio_array = np.concatenate(audio_data, axis=0)
        audio_array = audio_array.flatten()

        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            audio_int16 = (audio_array * 32767).astype(np.int16)
            wavfile.write(temp_path, sample_rate, audio_int16)

        # Транскрибируем
        print("Транскрипция...")
        result = model.transcribe(temp_path)

        # Удаляем временный файл
        os.unlink(temp_path)

        # Обрабатываем результат
        print(f"Тип результата: {type(result)}")
        print(f"Результат: {result}")

        if isinstance(result, list):
            transcription = result[0] if result else ""
        elif isinstance(result, dict):
            transcription = result.get("text", str(result))
        else:
            transcription = str(result) if result else ""

        print(f"Транскрипция: '{transcription}'")

        if transcription and transcription.strip():
            print(f"Вставляем текст: {transcription}")
            type_text(transcription)
        else:
            print("Пустой результат транскрипции")

    except Exception as e:
        print(f"Ошибка при транскрипции: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(icon, 'update_icon'):
            icon.update_icon("green", "GigaAM Transcriber - Ctrl+Alt+R")
        audio_data = []


def type_text(text: str):
    """Вставляет текст через буфер обмена используя xdotool."""
    print(f"\n{'='*50}")
    print(f"ВСТАВКА ТЕКСТА: {text[:80]}...")
    print(f"{'='*50}")

    # Даём время для переключения на нужное окно после остановки записи
    time.sleep(0.5)

    # Сохраняем старое содержимое буфера
    old_clipboard = ""
    try:
        old_clipboard = pyperclip.paste()
        print(f"✓ Старый буфер сохранён: {old_clipboard[:30]}...")
    except Exception as e:
        print(f"⚠ Не удалось прочитать буфер: {e}")

    # Копируем текст в буфер
    try:
        pyperclip.copy(text)
        # Проверяем что текст действительно скопирован
        check = pyperclip.paste()
        if check == text:
            print(f"✓ Текст скопирован в буфер обмена")
        else:
            print(f"⚠ Текст в буфере не совпадает!")
            print(f"  Ожидалось: {text[:50]}")
            print(f"  Получено: {check[:50]}")
    except Exception as e:
        print(f"✗ Ошибка копирования в буфер: {e}")
        return

    # Небольшая задержка для применения буфера
    time.sleep(0.15)

    # Получаем ID активного окна
    try:
        result = subprocess.run(
            ['xdotool', 'getactivewindow'],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0:
            window_id = result.stdout.strip()
            print(f"✓ Активное окно: {window_id}")
        else:
            window_id = None
            print(f"⚠ Не удалось получить ID окна: {result.stderr}")
    except Exception as e:
        window_id = None
        print(f"⚠ Ошибка получения ID окна: {e}")

    # Используем xdotool для вставки
    success = False
    try:
        print("→ Пробуем вставить через xdotool...")

        # Пробуем с указанием окна
        if window_id:
            result = subprocess.run(
                ['xdotool', 'key', '--window', window_id, 'ctrl+v'],
                capture_output=True,
                text=True,
                timeout=2
            )
        else:
            result = subprocess.run(
                ['xdotool', 'key', 'ctrl+v'],
                capture_output=True,
                text=True,
                timeout=2
            )

        if result.returncode == 0:
            print("✓ xdotool выполнен успешно")
            success = True
        else:
            print(f"✗ xdotool вернул код {result.returncode}")
            if result.stderr:
                print(f"  stderr: {result.stderr}")
            if result.stdout:
                print(f"  stdout: {result.stdout}")

    except subprocess.TimeoutExpired:
        print("✗ Таймаут при выполнении xdotool")
    except Exception as e:
        print(f"✗ Ошибка xdotool: {e}")

    # Fallback на pynput если xdotool не сработал
    if not success:
        try:
            print("→ Пробуем fallback через pynput...")
            keyboard.press(Key.ctrl)
            time.sleep(0.05)
            keyboard.press('v')
            time.sleep(0.05)
            keyboard.release('v')
            time.sleep(0.05)
            keyboard.release(Key.ctrl)
            print("✓ Вставка через pynput выполнена")
        except Exception as e2:
            print(f"✗ Ошибка pynput: {e2}")

    # Небольшая задержка
    time.sleep(0.2)

    # Восстанавливаем старый буфер
    try:
        pyperclip.copy(old_clipboard)
        print("✓ Старый буфер восстановлен")
    except Exception as e:
        print(f"⚠ Не удалось восстановить буфер: {e}")

    print(f"{'='*50}\n")


def toggle_recording(icon):
    """Переключает запись (для клика по иконке и горячей клавиши)."""
    global is_recording

    if model is None:
        print("Модель ещё загружается, подождите...")
        return

    if is_recording:
        if hasattr(icon, 'update_icon'):
            icon.update_icon("yellow", "GigaAM Transcriber (обработка...)")
        threading.Thread(target=stop_recording_and_transcribe, args=(icon,), daemon=True).start()
    else:
        if start_recording():
            if hasattr(icon, 'update_icon'):
                icon.update_icon("red", "GigaAM Transcriber (запись...)")


def on_icon_click(icon, item=None):
    """Обработчик клика по пункту меню."""
    toggle_recording(icon)


def cleanup():
    """Очистка ресурсов при выходе."""
    global is_recording, keyboard_listener, tray_icon

    print("\nЗавершение работы...")

    # Останавливаем запись
    if is_recording:
        stop_recording()

    # Останавливаем слушатель клавиатуры
    if keyboard_listener:
        try:
            keyboard_listener.stop()
        except:
            pass

    # Останавливаем иконку трея
    if tray_icon:
        try:
            tray_icon.hide()
        except:
            pass


def on_quit(icon, item):
    """Выход из приложения."""
    from PyQt6.QtWidgets import QApplication
    cleanup()
    QApplication.quit()


# Горячая клавиша: Ctrl+Alt+R (работает на любой раскладке)
# Используем vk (virtual key) код для 'R' = 0x52 на Windows, или keycode
HOTKEY_MODIFIERS = {Key.ctrl_l, Key.alt_l}


def is_r_key(key):
    """Проверяет, является ли клавиша буквой R (на любой раскладке)."""
    # Проверяем по символу (английская раскладка)
    if hasattr(key, "char") and key.char and key.char.lower() in ("r", "к"):
        return True
    # Проверяем по vk коду (работает на любой раскладке)
    if hasattr(key, "vk") and key.vk == 0x52:  # VK_R
        return True
    # Для Linux проверяем scancode
    if isinstance(key, KeyCode) and hasattr(key, "_scan"):
        # Scancode для R обычно 19 или 27
        return key._scan in (19, 27)
    return False


def on_key_press(key):
    """Обработчик нажатия клавиши."""
    global current_keys

    # Добавляем модификаторы
    if key in (Key.ctrl_l, Key.ctrl_r):
        current_keys.add(Key.ctrl_l)
    elif key in (Key.alt_l, Key.alt_r):
        current_keys.add(Key.alt_l)

    # Проверяем комбинацию Ctrl+Alt+R
    try:
        if is_r_key(key):
            if HOTKEY_MODIFIERS.issubset(current_keys):
                if tray_icon:
                    toggle_recording(tray_icon)
    except Exception as e:
        print(f"Ошибка горячей клавиши: {e}")


def on_key_release(key):
    """Обработчик отпускания клавиши."""
    global current_keys

    if key in (Key.ctrl_l, Key.ctrl_r):
        current_keys.discard(Key.ctrl_l)
    elif key in (Key.alt_l, Key.alt_r):
        current_keys.discard(Key.alt_l)




def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения."""
    cleanup()
    sys.exit(0)


def main():
    """Главная функция."""
    global tray_icon, keyboard_listener

    print("=" * 50)
    print("GigaAM Transcriber v3")
    print("=" * 50)
    print()
    print("Приложение запускается...")
    print("- Горячая клавиша: Ctrl+Alt+R - начать/остановить запись")
    print("- Клик по иконке в трее - начать/остановить запись")
    print()

    # Регистрируем обработчики завершения
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Импортируем PyQt6
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QPixmap, QAction
    from PyQt6.QtCore import QTimer

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Конвертируем PIL Image в QPixmap
    def pil_to_qpixmap(pil_image):
        """Конвертирует PIL Image в QPixmap."""
        import io
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        qpixmap = QPixmap()
        qpixmap.loadFromData(buffer.getvalue())
        return qpixmap

    # Создаём иконку трея
    tray = QSystemTrayIcon()
    tray.setIcon(QIcon(pil_to_qpixmap(create_icon_image("gray"))))
    tray.setToolTip("GigaAM Transcriber (загрузка...)")

    # Создаём меню
    menu = QMenu()

    record_action = QAction("⏺ НАЧАТЬ ЗАПИСЬ", None)
    record_action.triggered.connect(lambda: on_icon_click(tray))
    menu.addAction(record_action)

    menu.addSeparator()

    quit_action = QAction("Выход", None)
    quit_action.triggered.connect(lambda: on_quit(tray, None))
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    # Обработчик клика по иконке
    def on_tray_activated(reason):
        """Обработчик активации иконки трея."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Левый клик
            print("Клик по иконке!")
            toggle_recording(tray)

    tray.activated.connect(on_tray_activated)
    tray.show()

    tray_icon = tray

    # Функция обновления иконки и меню
    def update_tray_icon(color, tooltip):
        """Обновляет иконку трея."""
        tray.setIcon(QIcon(pil_to_qpixmap(create_icon_image(color))))
        tray.setToolTip(tooltip)
        # Обновляем текст пункта меню
        if is_recording:
            record_action.setText("⏹ ОСТАНОВИТЬ ЗАПИСЬ")
        else:
            record_action.setText("⏺ НАЧАТЬ ЗАПИСЬ")

    # Сохраняем функцию для использования в других местах
    tray.update_icon = update_tray_icon

    # Загрузка модели в отдельном потоке
    def load_and_update():
        if load_model():
            QTimer.singleShot(0, lambda: update_tray_icon("green", "GigaAM Transcriber - Ctrl+Alt+R"))
            print("\nГотов к записи! Нажмите Ctrl+Alt+R или кликните по иконке")
        else:
            QTimer.singleShot(0, lambda: update_tray_icon("gray", "GigaAM Transcriber (ошибка)"))
            print("\nОшибка загрузки модели!")

    threading.Thread(target=load_and_update, daemon=True).start()

    # Слушатель горячих клавиш
    keyboard_listener = KeyboardListener(on_press=on_key_press, on_release=on_key_release)
    keyboard_listener.start()

    try:
        # Запускаем приложение
        sys.exit(app.exec())
    finally:
        cleanup()


if __name__ == "__main__":
    main()
