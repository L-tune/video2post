import os
import logging
import asyncio
import re
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from .download_manager import DownloadManager
from .transcription import WhisperTranscriber
from .content_generator import ContentGenerator
from .youtube_subtitles import YouTubeSubtitlesExtractor

logger = logging.getLogger(__name__)

# Создаем кастомный фильтр для YouTube ссылок
def youtube_link_filter(update):
    """
    Фильтр для определения YouTube ссылок.
    
    Args:
        update: Обновление от Telegram
        
    Returns:
        bool: True, если сообщение содержит YouTube ссылку
    """
    if not update.message or not update.message.text:
        return False
        
    # Регулярное выражение для поиска YouTube ссылок
    youtube_pattern = r'(https?://)?(www\.)?(youtube\.com|youtu\.be|youtube\.com/shorts)/[\w\-?=&./%]+'
    return bool(re.search(youtube_pattern, update.message.text))

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
        
        # Логирование информации о ключах для отладки
        logger.info(f"Получен ключ OpenAI API: {openai_api_key[:10]}...")
        self.openai_api_key = openai_api_key
        
        # Логируем информацию о ключе Claude, если он предоставлен
        use_claude = False
        if claude_api_key:
            logger.info(f"Получен ключ Claude API: {claude_api_key[:10]}...")
            use_claude = True
        self.claude_api_key = claude_api_key
        
        self.temp_folder = temp_folder
        self.output_folder = output_folder
        
        # Создание папок, если они не существуют
        os.makedirs(temp_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)
        
        # Инициализация сервисов
        self.download_manager = DownloadManager(temp_folder)
        
        # Проверка ключа OpenAI перед передачей
        if not openai_api_key or openai_api_key == "OPENAI_API_KEY":
            logger.error("Некорректный ключ OpenAI API")
            raise ValueError("Некорректный ключ OpenAI API")
        
        logger.info(f"Инициализация транскрибера с ключом OpenAI: {openai_api_key[:10]}...")    
        self.transcriber = WhisperTranscriber(openai_api_key)
        
        # Инициализация экстрактора субтитров YouTube
        self.youtube_extractor = YouTubeSubtitlesExtractor(
            openai_api_key=openai_api_key,
            claude_api_key=claude_api_key,
            use_claude=use_claude
        )
        
        if use_claude:
            logger.info(f"Инициализация генератора контента с Claude API")
            self.content_generator = ContentGenerator(
                api_key=openai_api_key,
                use_claude=True,
                claude_api_key=claude_api_key
            )
        else:
            logger.info(f"Инициализация генератора контента с OpenAI API")
            self.content_generator = ContentGenerator(
                api_key=openai_api_key,
                use_claude=False
            )
        
        # Инициализация приложения
        self.application = Application.builder().token(token).build()
        
        # Регистрация обработчиков
        self.register_handlers()
    
    def register_handlers(self):
        """Регистрация обработчиков сообщений"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Обработчик видео сообщений
        self.application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, self.process_video))
        
        # Обработчик для YouTube ссылок с использованием кастомного фильтра
        # Важно: используем правильный способ объявления фильтра
        self.application.add_handler(MessageHandler(youtube_link_filter, self.process_youtube_link))
        
        # Обработчик для любых других текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        await update.message.reply_text(
            f"Привет, {user.first_name}! Я бот для преобразования видео в текстовые посты.\n\n"
            f"Отправьте мне видеофайл или ссылку на YouTube видео, и я создам готовый пост на основе его содержания."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        await update.message.reply_text(
            "Как пользоваться ботом:\n\n"
            "1. Отправьте видеофайл (до 20 МБ) или ссылку на YouTube видео\n"
            "2. Дождитесь обработки (может занять некоторое время в зависимости от длины видео)\n"
            "3. Получите готовый текстовый пост\n\n"
            "Поддерживаемые форматы:\n"
            "- Видео: MP4, MOV, AVI\n"
            "- YouTube ссылки: любой формат (youtu.be, youtube.com/watch, youtube.com/shorts)\n\n"
            "Команды:\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать справку"
        )
    
    async def process_youtube_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик получения YouTube ссылки"""
        try:
            youtube_url = update.message.text
            
            # Уведомление о начале обработки
            message = await update.message.reply_text("Получена ссылка на YouTube видео. Начинаю обработку...")
            
            # Извлечение субтитров из YouTube видео
            await message.edit_text("Получаю субтитры из видео...")
            subtitles = await self.youtube_extractor.get_subtitles(youtube_url)
            
            if not subtitles:
                await message.edit_text("Не удалось получить субтитры из видео. Возможно, они отключены или недоступны.")
                return
            
            # Генерация саммари из субтитров
            await message.edit_text("Анализирую субтитры и готовлю саммари...")
            summary = await self.youtube_extractor.generate_summary(subtitles)
            
            # Создание текстового поста на основе саммари
            await message.edit_text("Генерирую пост на основе ключевых фактов...")
            post_content = await self.content_generator.generate_post(summary)
            
            # Отправка результата
            await message.edit_text("Готово! Вот ваш пост:")
            await update.message.reply_text(post_content)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке YouTube видео: {e}")
            await update.message.reply_text(f"Произошла ошибка при обработке YouTube видео: {str(e)}")
    
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
            await message.edit_text("Генерирую пост на основе расшифровки...")
            post_content = await self.content_generator.generate_post(transcription)
            
            # Отправка результата
            await message.edit_text("Готово! Вот ваш пост:")
            await update.message.reply_text(post_content)
            
            # Очистка временных файлов
            os.remove(video_path)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео: {e}")
            await update.message.reply_text(f"Произошла ошибка при обработке видео: {str(e)}")
    
    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик текстовых сообщений"""
        await update.message.reply_text(
            "Пожалуйста, отправьте мне видеофайл или ссылку на YouTube видео для обработки.\n"
            "Используйте /help для получения инструкций."
        )
    
    async def start(self):
        """Запуск бота"""
        logger.info("Запуск Telegram бота...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        try:
            # Ожидание нажатия Ctrl+C для завершения
            await asyncio.Event().wait()
        finally:
            # Корректное завершение работы бота
            await self.application.stop()
            await self.application.shutdown() 