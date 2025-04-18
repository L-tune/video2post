import os
import logging
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from .download_manager import DownloadManager
from .transcription import Transcription
from .content_generator import ContentGenerator

logger = logging.getLogger(__name__)

class TelegramBot:
    """Класс Telegram бота для обработки видео и генерации постов"""
    
    def __init__(self, token, openai_api_key, claude_api_key=None, temp_folder="temp", output_folder="output"):
        """
        Инициализация бота.
        
        Args:
            token (str): Токен Telegram бота
            openai_api_key (str): API ключ OpenAI
            claude_api_key (str, optional): API ключ Claude
            temp_folder (str): Папка для временных файлов
            output_folder (str): Папка для выходных файлов
        """
        self.token = token
        self.openai_api_key = openai_api_key
        self.claude_api_key = claude_api_key
        self.temp_folder = temp_folder
        self.output_folder = output_folder
        
        # Создание папок, если они не существуют
        os.makedirs(temp_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)
        
        # Инициализация сервисов
        self.download_manager = DownloadManager(temp_folder)
        self.transcriber = Transcription(openai_api_key, claude_api_key, use_claude=True)
        self.content_generator = ContentGenerator(openai_api_key, claude_api_key)
        
        # Инициализация приложения
        self.application = Application.builder().token(token).build()
        
        # Регистрация обработчиков
        self.register_handlers()
        
    def register_handlers(self):
        """Регистрация обработчиков команд и сообщений"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, self.process_video))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        await update.message.reply_text(
            f"Привет, {user.mention_html()}! Я бот для создания текстовых постов из видео. "
            f"Отправь мне видеофайл, и я преобразую его в пост для социальных сетей."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        await update.message.reply_text(
            "Я могу преобразовать видео в текстовый пост.\n\n"
            "Просто отправьте мне видеофайл, и я:\n"
            "1. Расшифрую речь из видео\n"
            "2. Сгенерирую на ее основе пост для социальных сетей\n"
            "3. Отправлю вам готовый пост\n\n"
            "Поддерживаются видеофайлы большинства популярных форматов."
        )
    
    async def process_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик получения видеофайла"""
        try:
            # Уведомление о начале обработки
            message = await update.message.reply_text("Получен видеофайл. Начинаю обработку...")
            
            # Получение файла
            if update.message.video:
                file = await update.message.video.get_file()
            else:
                file = await update.message.document.get_file()
            
            # Скачивание видео
            await message.edit_text("Скачиваю видео...")
            video_path = await self.download_manager.download_file(file)
            
            # Транскрипция видео
            await message.edit_text("Расшифровываю речь из видео... Это может занять некоторое время.")
            transcription = await self.transcriber.transcribe(video_path)
            
            # Создание текстового поста
            await message.edit_text("Генерирую пост на основе расшифровки с помощью Claude API...")
            post_content = await self.content_generator.generate_post(transcription, use_claude=True)
            
            # Отправка результата
            await message.edit_text("Готово! Вот ваш пост:")
            await update.message.reply_text(post_content)
            
            # Очистка временных файлов
            self.download_manager.cleanup(video_path)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео: {e}")
            await update.message.reply_text(f"Произошла ошибка при обработке видео: {str(e)}")
    
    async def start(self):
        """Запуск бота"""
        logger.info("Запуск бота")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Держим бота запущенным
        try:
            await asyncio.Event().wait()
        finally:
            await self.application.stop()
            await self.application.shutdown() 