import os
import sys
import asyncio
import logging
import signal
import dotenv
from src.telegram_bot import TelegramBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
dotenv.load_dotenv()

# Получение конфигурации из переменных окружения
config = {
    'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
    'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
    'AUTHORIZED_USER_IDS': os.getenv('AUTHORIZED_USER_IDS', '')
}

# Проверка наличия необходимых переменных окружения
required_env_vars = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']
missing_vars = [var for var in required_env_vars if not config.get(var)]

if missing_vars:
    logger.error(f"Не указаны обязательные переменные окружения: {', '.join(missing_vars)}")
    sys.exit(1)

# Функция для запуска бота
async def main():
    # Обработчик сигналов
    loop = asyncio.get_event_loop()
    
    # Создание бота
    bot = TelegramBot(config)
    
    # Обработка сигналов для корректного завершения
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.stop()))
    
    try:
        logger.info("Запуск бота...")
        await bot.start()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main()) 