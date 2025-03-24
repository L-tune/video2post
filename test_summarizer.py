import os
import sys
import asyncio
import logging
import dotenv
import tempfile
import subprocess
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

# Получение API ключа OpenAI
openai_api_key = os.getenv('OPENAI_API_KEY')

if not openai_api_key:
    logger.error("Не указан OPENAI_API_KEY в переменных окружения")
    sys.exit(1)

async def download_test_video(youtube_url, output_path):
    """
    Скачивает тестовое видео с YouTube.
    
    Args:
        youtube_url (str): URL YouTube видео
        output_path (str): Путь для сохранения видеофайла
    
    Returns:
        bool: True, если скачивание успешно, иначе False
    """
    try:
        logger.info(f"Скачивание тестового видео из {youtube_url}")
        
        # Скачиваем видео с помощью yt-dlp
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", 
            "-f", "best[height<=480]",  # Ограничиваем разрешение для уменьшения размера файла
            "-o", output_path,
            youtube_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error(f"Ошибка при скачивании видео: {stderr.decode()}")
            return False
        
        logger.info(f"Видео успешно скачано в {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при скачивании видео: {e}")
        return False

async def test_youtube_summary(youtube_url):
    """
    Тестирование суммаризации YouTube видео.
    
    Args:
        youtube_url (str): URL YouTube видео для тестирования
    """
    logger.info(f"Начинаю тестирование суммаризации для URL: {youtube_url}")
    
    try:
        # Инициализация процессора видео
        processor = VideoProcessor(openai_api_key=openai_api_key)
        
        # Обработка YouTube URL
        result = await processor.process_youtube_url(youtube_url)
        
        # Вывод результатов
        print("\n" + "="*50)
        print(f"🎬 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ДЛЯ: {youtube_url}")
        print("="*50)
        
        # Вывод информации о видео
        print(f"\n📌 Название видео: {result.get('video_title', 'Н/Д')}")
        print(f"📌 ID видео: {result.get('video_id', 'Н/Д')}")
        
        # Вывод саммари
        print("\n📝 САММАРИ:")
        print("-"*50)
        print(result.get('summary', 'Саммари не получено'))
        print("-"*50)
        
        # Вывод части транскрипции (первые 500 символов)
        transcript = result.get('transcript', '')
        print("\n📄 ЧАСТЬ ТРАНСКРИПЦИИ (первые 500 символов):")
        print("-"*50)
        print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
        print("-"*50)
        
        # Статистика
        summary_len = len(result.get('summary', ''))
        transcript_len = len(transcript)
        compression_ratio = round((summary_len / transcript_len) * 100, 2) if transcript_len > 0 else 0
        
        print(f"\n📊 СТАТИСТИКА:")
        print(f"- Длина транскрипции: {transcript_len} символов")
        print(f"- Длина саммари: {summary_len} символов")
        print(f"- Коэффициент сжатия: {compression_ratio}%")
        
        logger.info("Тестирование завершено успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        print(f"\n❌ ОШИБКА ТЕСТИРОВАНИЯ: {e}")
        return False

async def test_video_file(video_path):
    """
    Тестирование суммаризации локального видеофайла.
    
    Args:
        video_path (str): Путь к видеофайлу
    """
    logger.info(f"Начинаю тестирование суммаризации для видеофайла: {video_path}")
    
    try:
        # Инициализация процессора видео
        processor = VideoProcessor(openai_api_key=openai_api_key)
        
        # Обработка видеофайла
        result = await processor.process_video_file(video_path)
        
        # Вывод результатов
        print("\n" + "="*50)
        print(f"🎬 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ДЛЯ ВИДЕО: {os.path.basename(video_path)}")
        print("="*50)
        
        # Вывод информации о видео
        print(f"\n📌 Длительность: {result.get('duration', 0):.2f} секунд")
        
        # Вывод саммари
        print("\n📝 САММАРИ:")
        print("-"*50)
        print(result.get('summary', 'Саммари не получено'))
        print("-"*50)
        
        # Вывод части транскрипции (первые 500 символов)
        transcript = result.get('transcript', '')
        print("\n📄 ЧАСТЬ ТРАНСКРИПЦИИ (первые 500 символов):")
        print("-"*50)
        print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
        print("-"*50)
        
        # Статистика
        summary_len = len(result.get('summary', ''))
        transcript_len = len(transcript)
        compression_ratio = round((summary_len / transcript_len) * 100, 2) if transcript_len > 0 else 0
        
        print(f"\n📊 СТАТИСТИКА:")
        print(f"- Длина транскрипции: {transcript_len} символов")
        print(f"- Длина саммари: {summary_len} символов")
        print(f"- Коэффициент сжатия: {compression_ratio}%")
        
        logger.info("Тестирование завершено успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        print(f"\n❌ ОШИБКА ТЕСТИРОВАНИЯ: {e}")
        return False

async def main():
    # Настройка аргументов командной строки
    parser = argparse.ArgumentParser(description='Тестирование саммаризации видео')
    parser.add_argument('--youtube', help='URL YouTube видео для тестирования')
    parser.add_argument('--file', help='Путь к локальному видеофайлу')
    parser.add_argument('--download', action='store_true', help='Скачать тестовое видео с YouTube для локального тестирования')
    args = parser.parse_args()
    
    success = False
    
    # Тестовый URL по умолчанию
    youtube_url = args.youtube or "https://www.youtube.com/watch?v=UQYV8--TZqI"
    
    # Если указана опция скачивания, скачиваем тестовое видео и тестируем локальный файл
    if args.download:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            video_path = tmp_file.name
        
        download_success = await download_test_video(youtube_url, video_path)
        
        if download_success:
            try:
                # Тестируем локальный файл
                success = await test_video_file(video_path)
            finally:
                # Удаляем временный файл
                os.remove(video_path)
        else:
            print("\n❌ Не удалось скачать тестовое видео.")
            success = False
    
    # Если указан локальный файл, тестируем его
    elif args.file:
        if not os.path.exists(args.file):
            print(f"\n❌ Файл не найден: {args.file}")
            success = False
        else:
            success = await test_video_file(args.file)
    
    # Иначе тестируем YouTube URL
    else:
        success = await test_youtube_summary(youtube_url)
    
    if success:
        print("\n✅ Тест пройден успешно!")
    else:
        print("\n❌ Тест завершился с ошибкой.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 