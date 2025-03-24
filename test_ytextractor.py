#!/usr/bin/env python3
import asyncio
import logging
import sys
import os
from src.youtube_subtitles import YouTubeSubtitlesExtractor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    if len(sys.argv) < 2:
        print("Использование: python test_ytextractor.py <youtube_url>")
        return
    
    youtube_url = sys.argv[1]
    
    # Получаем API ключ из переменной окружения
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("Ошибка: Не установлена переменная окружения YOUTUBE_API_KEY")
        return
    
    logger.info(f"Тестирование извлечения субтитров для URL: {youtube_url}")
    
    # Создаем экстрактор с API ключом
    extractor = YouTubeSubtitlesExtractor(api_key=api_key)
    
    # Получаем субтитры
    try:
        result = await extractor.get_subtitles(youtube_url)
        
        if result and result.get("transcript"):
            transcript = result["transcript"]
            video_title = result["video_title"]
            video_id = result["video_id"]
            
            logger.info(f"Видео ID: {video_id}")
            logger.info(f"Название: {video_title}")
            logger.info(f"Получено субтитров: {len(transcript)} символов")
            
            # Выводим первые 200 символов
            if transcript:
                print("\nПервые 200 символов субтитров:")
                print(transcript[:200] + "...")
            else:
                print("\nСубтитры не найдены")
        else:
            logger.warning("Не удалось получить субтитры")
            print("\nСубтитры не найдены")
            
    except Exception as e:
        logger.error(f"Ошибка при получении субтитров: {e}")
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 