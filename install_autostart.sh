#!/bin/bash
# Скрипт установки автозапуска GigaAM Transcriber

set -e

# Получаем абсолютный путь к директории проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UV_PATH="$(which uv)"

# Создаем директорию автозапуска если её нет
mkdir -p ~/.config/autostart

# Создаем .desktop файл
cat > ~/.config/autostart/gigaam-transcriber.desktop << EOF
[Desktop Entry]
Type=Application
Name=GigaAM Transcriber
Comment=Голосовой ввод текста через GigaAM
Exec=$UV_PATH run --directory "$SCRIPT_DIR" transcriber.py
Icon=audio-input-microphone
Terminal=false
Categories=Utility;
X-KDE-autostart-after=panel
X-KDE-StartupNotify=false
Hidden=false
EOF

chmod +x ~/.config/autostart/gigaam-transcriber.desktop

echo "Автозапуск установлен: ~/.config/autostart/gigaam-transcriber.desktop"
echo "Приложение будет запускаться автоматически при входе в систему."
