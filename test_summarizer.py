#!/usr/bin/env python3
import asyncio
import logging
import sys
import os
from dotenv import load_dotenv
from src.summarizer import Summarizer

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    if len(sys.argv) < 2:
        print("Использование: python test_summarizer.py <youtube_url>")
        return
    
    youtube_url = sys.argv[1]
    
    # Получаем API ключи из переменных окружения
    youtube_api_key = os.getenv('YOUTUBE_API_KEY')
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    
    if not youtube_api_key:
        print("Ошибка: Не установлена переменная окружения YOUTUBE_API_KEY")
        return
        
    if not claude_api_key:
        print("Ошибка: Не установлена переменная окружения CLAUDE_API_KEY")
        return
    
    logger.info(f"Тестирование генерации саммари для URL: {youtube_url}")
    
    # Создаем саммарайзер
    summarizer = Summarizer(youtube_api_key=youtube_api_key, claude_api_key=claude_api_key)
    
    try:
        # Генерируем саммари
        result = await summarizer.generate_summary(youtube_url)
        
        if result:
            video_title = result["video_title"]
            video_id = result["video_id"]
            summary = result["summary"]
            transcript = result["transcript"]
            
            logger.info(f"Видео ID: {video_id}")
            logger.info(f"Название: {video_title}")
            logger.info(f"Длина субтитров: {len(transcript)} символов")
            logger.info(f"Длина саммари: {len(summary)} символов")
            
            print("\nНазвание видео:")
            print(video_title)
            print("\nСаммари:")
            print(summary)
            
            # Сохраняем результат в файл
            output_file = f"output/{video_id}_summary.txt"
            os.makedirs("output", exist_ok=True)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Название: {video_title}\n\n")
                f.write(f"ID видео: {video_id}\n\n")
                f.write("САММАРИ:\n")
                f.write(summary)
                f.write("\n\nИСХОДНЫЕ СУБТИТРЫ:\n")
                f.write(transcript)
            
            logger.info(f"Результат сохранен в файл: {output_file}")
            
        else:
            logger.error("Не удалось сгенерировать саммари")
            print("\nНе удалось сгенерировать саммари")
            
    except Exception as e:
        logger.error(f"Ошибка при генерации саммари: {e}")
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 