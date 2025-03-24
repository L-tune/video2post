# YouTube Video Summarizer

Сервис для генерации кратких и информативных саммари YouTube видео на основе их транскрипций с использованием Claude AI.

## Возможности

- Извлечение транскрипций из YouTube видео
- Получение информации о видео через YouTube Data API
- Генерация структурированных саммари с помощью Claude AI
- Поддержка русского и английского языков
- Сохранение результатов в текстовые файлы

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/youtube-summarizer.git
cd youtube-summarizer
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` и добавьте в него API ключи:
```
YOUTUBE_API_KEY=your_youtube_api_key
CLAUDE_API_KEY=your_claude_api_key
```

## Использование

Запустите скрипт с URL YouTube видео:

```bash
python test_summarizer.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Результат будет выведен в консоль и сохранен в файл `output/VIDEO_ID_summary.txt`.

## Требования

- Python 3.8+
- YouTube Data API ключ
- Claude API ключ

## Структура проекта

```
.
├── src/
│   └── summarizer.py     # Основной класс для генерации саммари
├── test_summarizer.py    # Скрипт для тестирования
├── requirements.txt      # Зависимости проекта
└── README.md            # Документация
```

## Лицензия

MIT 