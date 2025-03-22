#!/usr/bin/env python3
import os
import asyncio
from dotenv import load_dotenv
from src.transcription import Transcription

# Загрузка переменных окружения
load_dotenv()

async def test_transcription():
    """
    Тестирование транскрипции аудио через Whisper API
    без запуска полного Telegram бота
    """
    # Получение API ключа из переменных окружения
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        print("Ошибка: OPENAI_API_KEY не найден в .env файле")
        return
    
    # Создание экземпляра класса транскрипции
    transcription = Transcription(openai_api_key)
    
    # Создание временной директории, если она не существует
    temp_folder = os.getenv("TEMP_FOLDER", "temp")
    os.makedirs(temp_folder, exist_ok=True)
    
    # Тестовый аудиофайл - можно использовать любой .mp3 или .wav файл
    # Создадим файл с уведомлением, если его нет
    test_audio_file = os.path.join(temp_folder, "test_audio.mp3")
    
    if not os.path.exists(test_audio_file):
        print(f"Тестовый аудиофайл не найден: {test_audio_file}")
        print("Пожалуйста, поместите аудиофайл в папку temp с именем test_audio.mp3")
        print("Или укажите путь к существующему аудиофайлу в коде")
        return
    
    print(f"Начинаю транскрипцию файла: {test_audio_file}")
    try:
        # Транскрипция аудиофайла
        transcription_text = await transcription.transcribe_audio(test_audio_file)
        
        print("\n=== Результат транскрипции ===\n")
        print(transcription_text)
        print("\n=== Конец транскрипции ===\n")
        print("Транскрипция успешно завершена!")
    
    except Exception as e:
        print(f"Ошибка при транскрипции: {e}")

if __name__ == "__main__":
    asyncio.run(test_transcription()) 