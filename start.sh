#!/bin/bash
# Скрипт для запуска бота

# Проверяем наличие необходимой библиотеки anthropic
if ! pip show anthropic > /dev/null 2>&1; then
    echo "Устанавливаем пакет anthropic..."
    pip install anthropic==0.9.0 httpx==0.23.3
fi

echo "Запускаем бота..."
python bot.py
