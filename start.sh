#!/bin/bash
# Скрипт для запуска бота с предварительной проверкой наличия anthropic

echo "Проверяем наличие библиотеки anthropic..."
python -c "import anthropic" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "Библиотека anthropic не найдена, устанавливаем..."
    pip install anthropic==0.49.0
    echo "Установка завершена"
fi

echo "Запускаем бота..."
python bot.py
