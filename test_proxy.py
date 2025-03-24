import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
from src.video_processor import VideoProcessor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_proxy.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def test_youtube_subtitles(youtube_url, proxy=None):
    """
    Тестирует получение субтитров с YouTube с использованием прокси.
    
    Args:
        youtube_url (str): URL видео на YouTube
        proxy (str, optional): прокси-сервер в формате http://user:pass@host:port
    """
    try:
        logger.info(f"Начинаем тест получения субтитров для: {youtube_url}")
        
        # Создаем временную директорию если её нет
        temp_folder = "temp"
        os.makedirs(temp_folder, exist_ok=True)
        
        # Инициализация процессора видео
        if proxy:
            logger.info(f"Используем прокси: {proxy[:10]}...")
        else:
            logger.info("Прокси не предоставлен, используем прямое подключение")
            
        video_processor = VideoProcessor(temp_folder=temp_folder, proxy=proxy)
        
        # Обработка YouTube URL
        result = await video_processor.process_youtube_url(youtube_url)
        
        # Анализ результата
        video_id = result.get('video_id')
        transcription = result.get('transcription', '')
        segments = result.get('transcript_segments', [])
        source = "через прокси" if result.get('source') == 'proxy' else "напрямую"
        
        logger.info(f"Результаты теста для видео ID: {video_id}")
        logger.info(f"Получено через: {source}")
        logger.info(f"Количество сегментов субтитров: {len(segments)}")
        logger.info(f"Объем транскрипции: {len(transcription)} символов")
        
        # Выводим первые 10 сегментов для анализа
        logger.info("Первые 10 сегментов субтитров:")
        for i, segment in enumerate(segments[:10]):
            logger.info(f"{i+1}. [{segment.get('start')}]: {segment.get('text')}")
        
        # Выводим первые 200 символов транскрипции
        logger.info(f"Начало транскрипции: {transcription[:200]}...")
        
        return {
            "success": True,
            "video_id": video_id,
            "source": source,
            "segments_count": len(segments),
            "transcription_length": len(transcription),
            "transcription_preview": transcription[:200]
        }
    
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

async def main():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем URL видео и прокси из аргументов командной строки или используем значения по умолчанию
    youtube_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=UQYV8--TZqI"
    
    # Получаем прокси из переменных окружения или аргументов
    proxy = None
    if len(sys.argv) > 2:
        proxy = sys.argv[2]
    else:
        proxy = os.getenv("YOUTUBE_PROXY")
    
    # Запускаем тест
    result = await test_youtube_subtitles(youtube_url, proxy)
    
    # Выводим результат
    if result["success"]:
        print("\n=== ТЕСТ ВЫПОЛНЕН УСПЕШНО ===")
        print(f"Видео ID: {result['video_id']}")
        print(f"Получено: {result['source']}")
        print(f"Количество сегментов: {result['segments_count']}")
        print(f"Размер транскрипции: {result['transcription_length']} символов")
        print("\nФрагмент транскрипции:")
        print(result['transcription_preview'])
    else:
        print("\n=== ТЕСТ ЗАВЕРШИЛСЯ С ОШИБКОЙ ===")
        print(f"Причина: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main()) 