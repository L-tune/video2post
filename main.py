import os
import logging
import asyncio
from dotenv import load_dotenv
from src.telegram_bot import TelegramBot

# Загрузка переменных окружения из файла .env
load_dotenv()

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

# Определение логгера
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    # Получение переменных окружения
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    temp_folder = os.getenv("TEMP_FOLDER", "temp")
    output_folder = os.getenv("OUTPUT_FOLDER", "output")
    
    # Проверка наличия токена Telegram
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в .env файле.")
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле.")
    
    # Проверка наличия API ключа OpenAI
    if not openai_api_key:
        logger.error("OPENAI_API_KEY не найден в .env файле.")
        raise ValueError("OPENAI_API_KEY не найден в .env файле.")
    
    # Создание и запуск бота
    bot = TelegramBot(
        token=telegram_token, 
        openai_api_key=openai_api_key,
        claude_api_key=claude_api_key,
        temp_folder=temp_folder,
        output_folder=output_folder
    )
    
    logger.info("Запуск бота...")
    await bot.start()

if __name__ == "__main__":
    setup_logging()
    asyncio.run(main()) 