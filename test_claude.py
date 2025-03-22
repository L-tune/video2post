#!/usr/bin/env python3
import os
import asyncio
from dotenv import load_dotenv
from src.content_generator import ContentGenerator

# Загрузка переменных окружения
load_dotenv()

async def test_claude_generation():
    """
    Тестирование генерации поста с использованием Claude API
    без запуска полного Telegram бота
    """
    # Получение API ключей из переменных окружения
    openai_api_key = os.getenv("OPENAI_API_KEY")
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    
    if not openai_api_key:
        print("Ошибка: OPENAI_API_KEY не найден в .env файле")
        return
    
    if not claude_api_key:
        print("Ошибка: CLAUDE_API_KEY не найден в .env файле")
        return
    
    # Создание генератора контента
    content_generator = ContentGenerator(openai_api_key, claude_api_key)
    
    # Тестовая транскрипция
    test_transcription = """
    Привет! Сегодня я хочу рассказать о нейронных сетях и их применении в задачах компьютерного зрения.
    Нейронные сети - это математические модели, вдохновленные структурой биологических нейронных сетей.
    Они состоят из слоев нейронов, которые связаны между собой весами.
    В задачах компьютерного зрения особенно популярны сверточные нейронные сети или CNN.
    Они используют операцию свертки для извлечения признаков из изображений.
    Современные архитектуры, такие как ResNet, EfficientNet и Vision Transformer, достигают потрясающих результатов
    в таких задачах, как классификация изображений, обнаружение объектов и сегментация.
    
    Если вам интересно узнать больше о нейронных сетях и компьютерном зрении, дайте знать в комментариях!
    """
    
    print("Начинаю генерацию поста с использованием Claude API...")
    try:
        # Генерация поста с использованием Claude API
        post_content = await content_generator.generate_post(test_transcription, use_claude=True)
        
        print("\n=== Сгенерированный пост ===\n")
        print(post_content)
        print("\n=== Конец поста ===\n")
        print("Генерация успешно завершена!")
    
    except Exception as e:
        print(f"Ошибка при генерации поста: {e}")

if __name__ == "__main__":
    asyncio.run(test_claude_generation()) 