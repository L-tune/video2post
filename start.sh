#!/bin/bash
# Скрипт для запуска бота

# Проверяем наличие необходимой библиотеки anthropic
if ! pip show anthropic > /dev/null 2>&1; then
    echo "Устанавливаем пакет anthropic..."
    pip install anthropic==0.19.1 httpx>=0.24.1 httpcore>=0.17.0
fi

echo "Запускаем бота..."
python bot.py
