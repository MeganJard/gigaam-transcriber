# Инструкции по выкладке на GitHub

## Создание репозитория на GitHub

1. Перейдите на https://github.com/new
2. Укажите название репозитория: `gigaam-transcriber`
3. Добавьте описание: "Голосовой ввод текста на основе GigaAM v3"
4. Выберите Public или Private
5. **НЕ** создавайте README, .gitignore или LICENSE (они уже есть в проекте)
6. Нажмите "Create repository"

## Загрузка кода

После создания репозитория выполните команды:

```bash
cd "/home/meganjard/Рабочий стол/giga am transcriber"

# Добавьте remote (замените YOUR_USERNAME на ваш GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/gigaam-transcriber.git

# Загрузите код
git push -u origin main
```

## Обновление ссылок в README

После создания репозитория замените в файлах:

1. **README.md** - замените `your-username` на ваш GitHub username
2. **pyproject.toml** - замените `your-username` на ваш GitHub username

Затем закоммитьте изменения:

```bash
git add README.md pyproject.toml
git commit -m "Update repository URLs"
git push
```

## Настройка GitHub Topics

В настройках репозитория на GitHub добавьте topics:
- `speech-recognition`
- `voice-input`
- `gigaam`
- `python`
- `linux`
- `kde`
- `transcription`

## Структура проекта готова для GitHub

```
gigaam-transcriber/
├── .gitignore              # Исключения для git
├── LICENSE                 # MIT лицензия
├── README.md               # Документация
├── CONTRIBUTING.md         # Инструкции по выкладке (этот файл)
├── pyproject.toml          # Конфигурация uv
├── requirements.txt        # Python зависимости
├── install_autostart.sh    # Скрипт установки автозапуска
└── transcriber.py          # Основной код приложения
```

## Что проигнорировано

Следующие файлы и директории не попадут в репозиторий (согласно .gitignore):
- `.venv/`, `venv/` - виртуальные окружения
- `.claude/` - служебная директория Claude Code
- `__pycache__/`, `*.pyc` - Python cache
- `*.wav`, `*.tmp` - временные файлы
- `run.sh`, `gigaam-transcriber.desktop` - старые файлы

## Рекомендации

1. Добавьте скриншот или GIF с демонстрацией работы приложения
2. Создайте GitHub Release для версии 1.0.0
3. Настройте GitHub Actions для автоматического тестирования (опционально)
