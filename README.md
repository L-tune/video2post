# Video2Post Bot для Telegram

Бот для автоматического преобразования видеофайлов в текстовые посты для Telegram.

## Возможности

- Обработка видеофайлов форматов MP4, MOV, AVI (до 2 ГБ)
- Извлечение аудиодорожки из видео
- Транскрипция аудио с помощью OpenAI Whisper API
- Генерация структурированного поста на основе транскрипции с помощью GPT-4
- Поддержка маркдаун-разметки для Telegram

## Требования

- Python 3.9+
- FFmpeg (для работы с аудио и видео)
- Ключ API OpenAI

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/video2post.git
cd video2post
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Установите FFmpeg (если еще не установлен):

   - Для macOS (с использованием Homebrew):
   ```bash
   brew install ffmpeg
   ```

   - Для Ubuntu/Debian:
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```

4. Создайте файл `.env` на основе `.env.example` и добавьте необходимые переменные окружения:
```bash
cp .env.example .env
```

5. Отредактируйте файл `.env`, добавив свой ключ API OpenAI:
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
TEMP_FOLDER=./temp
OUTPUT_FOLDER=./output
```

## Запуск

```bash
python main.py
```

## Использование

1. Найдите бота в Telegram и отправьте команду `/start`
2. Отправьте боту видеофайл (MP4, MOV или AVI)
3. Дождитесь завершения обработки
4. Получите готовый пост, который можно сразу публиковать в Telegram

## Деплой на Render.com

1. Создайте новый Web Service на Render.com
2. Укажите ссылку на ваш GitHub репозиторий
3. Тип: Web Service
4. В настройках окружения укажите переменные из файла `.env`
5. Команда для сборки: `pip install -r requirements.txt`
6. Команда для запуска: `python main.py`

## Структура проекта

```
video2post/
├── main.py              # Основной файл приложения
├── requirements.txt     # Зависимости проекта
├── .env.example         # Пример конфигурации
├── .env                 # Конфигурация (не включена в репозиторий)
├── README.md            # Документация
└── src/                 # Исходный код
    ├── __init__.py
    ├── video_processor.py      # Обработка видео
    ├── transcription.py        # Транскрипция с Whisper
    └── content_generator.py    # Генерация контента с GPT-4
```

## Лицензия

MIT 