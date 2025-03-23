#!/bin/bash
# Скрипт для запуска бота с предварительной проверкой наличия anthropic

echo "Проверяем и устанавливаем все необходимые зависимости..."

# Явная установка всех необходимых зависимостей, даже если они уже установлены
pip install anthropic==0.49.0
pip install python-telegram-bot==20.5
pip install openai==1.68.2
pip install python-dotenv==1.0.0
pip install moviepy==1.0.3
pip install ffmpeg-python==0.2.0

echo "Запускаем бота..."
python bot.py
