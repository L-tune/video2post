import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from src.telegram_bot import TelegramBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

async def main():
    try:
        # Загрузка переменных окружения из .env файла
        load_dotenv()
        
        # Получение токенов из переменных окружения
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        claude_api_key = os.getenv("CLAUDE_API_KEY", None)
        
        # Отладочная информация
        logger.info(f"Загруженный OPENAI_API_KEY: {openai_api_key[:10]}...")
        
        # Выводим информацию о ключе Claude
        if claude_api_key:
            logger.info(f"Загруженный CLAUDE_API_KEY: {claude_api_key[:10]}...")
        else:
            logger.error("CLAUDE_API_KEY не найден или пустой")
        
        # Проверка наличия токенов
        if not telegram_token:
            logger.error("Токен Telegram бота не найден. Установите TELEGRAM_BOT_TOKEN в .env файле.")
            sys.exit(1)
            
        if not openai_api_key:
            logger.error("Ключ API OpenAI не найден. Установите OPENAI_API_KEY в .env файле.")
            sys.exit(1)
            
        # Проверка формата ключа API OpenAI
        if not openai_api_key.startswith("sk-"):
            logger.warning(f"Неверный формат ключа OpenAI API. Ключ должен начинаться с 'sk-': {openai_api_key[:10]}...")
        
        # Инициализация и запуск бота
        logger.info("Запуск бота...")
        bot = TelegramBot(
            token=telegram_token, 
            openai_api_key=openai_api_key,
            claude_api_key=claude_api_key
        )
        await bot.start()
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Запуск асинхронной функции main
    asyncio.run(main()) 