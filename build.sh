#!/bin/bash
# Скрипт для сборки проекта на Render

echo "Начинаем установку зависимостей..."

# Устанавливаем только нужные пакеты явно, игнорируя requirements.txt
pip install anthropic==0.49.0
pip install python-telegram-bot==20.5
pip install openai==1.68.2
pip install python-dotenv==1.0.0
pip install moviepy==1.0.3
pip install ffmpeg-python==0.2.0
pip install tqdm==4.67.1
pip install requests==2.31.0
pip install aiohttp==3.9.3
pip install numpy==1.26.4
pip install Pillow==10.2.0

echo "Установка завершена успешно"
