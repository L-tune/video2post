import os
import sys
import asyncio
import logging
import dotenv
import tempfile
import argparse
from src.video_processor import VideoProcessor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("test.log")
    ]
)

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
dotenv.load_dotenv()

async def test_youtube_transcript(youtube_url, proxy=None):
    """
    Тестирование получения транскрипции из YouTube видео.
    
    Args:
        youtube_url (str): URL YouTube видео для тестирования
        proxy (str, optional): Прокси для YouTube API
    """
    logger.info(f"Начинаю тестирование получения транскрипции для URL: {youtube_url}")
    
    try:
        # Инициализация видео процессора
        processor = VideoProcessor(proxy=proxy)
        
        # Получение данных из YouTube
        result = await processor.process_youtube_url(youtube_url)
        
        # Вывод результатов
        print("\n" + "="*50)
        print(f"🎬 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ДЛЯ: {youtube_url}")
        print("="*50)
        
        # Вывод информации о видео
        print(f"\n📌 Название видео: {result.get('video_title', 'Н/Д')}")
        print(f"📌 ID видео: {result.get('video_id', 'Н/Д')}")
        
        # Вывод части транскрипции (первые 500 символов)
        transcript = result.get('transcript', '')
        print("\n📄 ТРАНСКРИПЦИЯ (первые 500 символов):")
        print("-"*50)
        print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
        print("-"*50)
        
        # Статистика
        transcript_len = len(transcript)
        
        print(f"\n📊 СТАТИСТИКА:")
        print(f"- Длина транскрипции: {transcript_len} символов")
        
        logger.info("Тестирование завершено успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        print(f"\n❌ ОШИБКА ТЕСТИРОВАНИЯ: {e}")
        return False

async def main():
    # Настройка аргументов командной строки
    parser = argparse.ArgumentParser(description='Тестирование получения транскрипции видео')
    parser.add_argument('--youtube', help='URL YouTube видео для тестирования')
    parser.add_argument('--proxy', help='Прокси-сервер для доступа к YouTube API (http://user:pass@host:port)')
    args = parser.parse_args()
    
    # Тестовый URL по умолчанию
    youtube_url = args.youtube or "https://www.youtube.com/watch?v=UQYV8--TZqI"
    proxy = args.proxy
    
    # Вывод информации о параметрах
    if proxy:
        print(f"Используем прокси: {proxy}")
    
    # Тестируем YouTube URL
    success = await test_youtube_transcript(youtube_url, proxy)
    
    if success:
        print("\n✅ Тест пройден успешно!")
    else:
        print("\n❌ Тест завершился с ошибкой.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 