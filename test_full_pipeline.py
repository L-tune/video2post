#!/usr/bin/env python3
import os
import asyncio
import logging
from dotenv import load_dotenv
from src.transcription import Transcription
from src.content_generator import ContentGenerator
from src.download_manager import DownloadManager

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

async def test_full_pipeline(video_path):
    """
    Тестирование полного конвейера обработки: видео -> аудио -> транскрипция -> пост
    без запуска Telegram бота
    """
    # Получение API ключей из переменных окружения
    openai_api_key = os.getenv("OPENAI_API_KEY")
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    
    if not openai_api_key:
        logger.error("OPENAI_API_KEY не найден в .env файле")
        return
    
    if not claude_api_key:
        logger.error("CLAUDE_API_KEY не найден в .env файле")
        return
    
    # Создание временных директорий
    temp_folder = os.getenv("TEMP_FOLDER", "temp")
    output_folder = os.getenv("OUTPUT_FOLDER", "output")
    os.makedirs(temp_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    
    # Проверка наличия видеофайла
    if not os.path.exists(video_path):
        logger.error(f"Видеофайл не найден: {video_path}")
        return
    
    logger.info(f"Начинаю обработку видео: {video_path}")
    
    try:
        # 1. Извлечение аудио из видео
        download_manager = DownloadManager(temp_folder)
        audio_path = await download_manager.extract_audio_from_video(video_path)
        logger.info(f"Аудио успешно извлечено: {audio_path}")
        
        # 2. Транскрипция аудио
        transcription_service = Transcription(openai_api_key)
        transcription_text = await transcription_service.transcribe_audio(audio_path)
        logger.info("Транскрипция успешно получена")
        
        # 3. Генерация поста
        content_generator = ContentGenerator(openai_api_key, claude_api_key)
        post_content = await content_generator.generate_post(transcription_text, use_claude=True)
        logger.info("Пост успешно сгенерирован")
        
        # 4. Сохранение результатов
        video_name = os.path.basename(video_path)
        base_name = os.path.splitext(video_name)[0]
        
        # Сохранение транскрипции
        transcript_path = os.path.join(output_folder, f"{base_name}_transcript.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcription_text)
        
        # Сохранение поста
        post_path = os.path.join(output_folder, f"{base_name}_post.txt")
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(post_content)
        
        logger.info(f"Транскрипция сохранена в: {transcript_path}")
        logger.info(f"Пост сохранен в: {post_path}")
        
        return {
            "transcription": transcription_text,
            "post": post_content,
            "transcript_path": transcript_path,
            "post_path": post_path
        }
    
    except Exception as e:
        logger.error(f"Ошибка в процессе обработки: {e}")
        return None

if __name__ == "__main__":
    # Проверка наличия тестового видеофайла
    test_video = os.path.join("temp", "test_video.mp4")
    
    if not os.path.exists(test_video):
        logger.info(f"Тестовый видеофайл не найден: {test_video}")
        logger.info("Пожалуйста, поместите видеофайл в папку temp с именем test_video.mp4")
        logger.info("Или укажите путь к существующему видеофайлу в коде")
        exit(1)
    
    result = asyncio.run(test_full_pipeline(test_video))
    
    if result:
        logger.info("Весь процесс успешно завершен!")
        
        # Вывод последних 10 строк транскрипции
        logger.info("\n--- Фрагмент транскрипции ---")
        with open(result["transcript_path"], "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(line.strip())
        
        # Вывод первых 10 строк поста
        logger.info("\n--- Фрагмент поста ---")
        with open(result["post_path"], "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[:10]:
                print(line.strip())
    else:
        logger.error("Процесс обработки завершился с ошибкой.") 