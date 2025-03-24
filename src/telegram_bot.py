import os
import logging
import re
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from .download_manager import DownloadManager
from .transcription import WhisperTranscriber
from .content_generator import ContentGenerator

logger = logging.getLogger(__name__)

# Паттерн для извлечения ID видео из YouTube URL
YOUTUBE_URL_PATTERN = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'

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
        
        # Обработчик для любых других сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        await update.message.reply_text(
            f"Привет, {user.first_name}! Я бот для преобразования видео в текстовые посты.\n\n"
            f"Отправьте мне видеофайл, и я создам готовый пост на основе его содержания."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        await update.message.reply_text(
            "Как пользоваться ботом:\n\n"
            "1. Отправьте видеофайл (до 20 МБ) или ссылку на YouTube видео\n"
            "2. Дождитесь обработки (может занять некоторое время в зависимости от длины видео)\n"
            "3. Получите готовый текстовый пост\n\n"
            "Поддерживаемые форматы:\n"
            "- Видеофайлы: MP4, MOV, AVI\n"
            "- YouTube: любые публичные видео с доступными субтитрами\n\n"
            "Команды:\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать справку"
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
        message_text = update.message.text
        
        # Проверяем, является ли сообщение ссылкой на YouTube
        youtube_match = re.search(YOUTUBE_URL_PATTERN, message_text)
        if youtube_match:
            youtube_url = youtube_match.group(0)
            logger.info(f"Обнаружена YouTube ссылка: {youtube_url}")
            
            # Извлекаем видео ID
            video_id = youtube_match.group(6)
            logger.info(f"Извлечен ID видео: {video_id}")
            
            # Очищаем URL от лишних параметров
            clean_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Очищенный URL: {clean_url}")
            
            message = await update.message.reply_text(f"🔍 Начинаю обработку YouTube видео: {clean_url}\nПожалуйста, подождите...")
            
            try:
                from .video_processor import VideoProcessor
                
                # Создаем экземпляр VideoProcessor с передачей ключа API
                video_processor = VideoProcessor(
                    temp_folder=self.temp_folder,
                    openai_api_key=self.openai_api_key
                )
                
                # Обрабатываем YouTube URL
                await message.edit_text("⏳ Получаю информацию о видео...")
                video_data = await video_processor.process_youtube_url(clean_url)
                
                transcription = video_data.get('transcription')
                
                # Если транскрипция получена успешно, генерируем пост
                if transcription:
                    await message.edit_text("⏳ Генерирую пост на основе транскрипции...")
                    post_content = await self.content_generator.generate_post(transcription)
                    
                    # Отправка результата
                    await message.edit_text("✅ Готово! Вот ваш пост:")
                    await update.message.reply_text(post_content)
                else:
                    await message.edit_text("❌ Не удалось получить транскрипцию для данного видео.")
            except Exception as e:
                logger.error(f"Ошибка при обработке YouTube URL: {e}", exc_info=True)
                await message.edit_text(f"❌ Не удалось обработать YouTube видео: {str(e)}")
                
        else:
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