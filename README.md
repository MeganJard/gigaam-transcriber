# GigaAM Transcriber

Приложение для голосового ввода текста на основе модели GigaAM v3 от Сбера. Работает в системном трее, записывает речь и автоматически вставляет транскрипцию в место курсора.

## Возможности

- Запись речи по клику на иконку в трее
- Транскрипция с помощью GigaAM v3 (с поддержкой пунктуации)
- Поддержка длинных записей 
- Автоматическая вставка текста в место курсора
- Визуальная индикация состояния цветом иконки
- Автозапуск при входе в систему

## Требования

- Linux (Fedora, Ubuntu, etc.)
- Python 3.10+
- xdotool
- Микрофон

## Установка

### 1. Системные зависимости

Fedora/RHEL:
```bash
sudo dnf install xdotool portaudio-devel
```

Ubuntu/Debian:
```bash
sudo apt install xdotool portaudio19-dev
```

### 2. Установка uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### 3. Клонирование и запуск

```bash
git clone https://github.com/MeganJard/gigaam-transcriber.git
cd gigaam-transcriber
uv sync
uv run transcriber.py
```

Первый запуск займёт время (~500MB) — скачивается PyTorch и модель GigaAM.

### 4. Автозапуск (опционально)

```bash
bash install_autostart.sh
```

## Использование

- **Левый клик** — начать/остановить запись
- **Правый клик** — меню с выходом

### Цвета иконки

- **Серый** — загрузка модели
- **Зелёный** — готов к записи
- **Красный** — идёт запись
- **Жёлтый** — транскрипция

## Логи

```bash
tail -f ~/.local/share/gigaam-transcriber/transcriber.log
```

## Лицензия

MIT
