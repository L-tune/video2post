import os
import logging
import re
import asyncio
import tempfile
from typing import List, Dict, Any, Optional, Union
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from src.youtube_subtitles import YouTubeSubtitlesExtractor
from src.video_processor import VideoProcessor

logger = logging.getLogger(__name__)

YOUTUBE_URL_PATTERN = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'

class TelegramBot:
    """Класс для взаимодействия с Telegram API."""
    
    def __init__(self, config):
        """
        Инициализирует бота с указанными конфигурациями.
        
        Args:
            config (dict): Словарь с конфигурациями
        """
        self.config = config
        self.bot_token = config.get('TELEGRAM_BOT_TOKEN')
        self.openai_api_key = config.get('OPENAI_API_KEY')
        self.authorized_user_ids = [int(uid) for uid in config.get('AUTHORIZED_USER_IDS', '').split(',') if uid]
        
        # Создаем временную директорию для файлов
        self.temp_folder = tempfile.mkdtemp()
        logger.info(f"Создана временная директория: {self.temp_folder}")
        
        # Инициализируем процессор видео
        self.video_processor = VideoProcessor(openai_api_key=self.openai_api_key)
        
        # Инициализируем обработчик YouTube ссылок
        self.youtube_extractor = YouTubeSubtitlesExtractor()
        
        logger.info("TelegramBot: Инициализирован")
    
    async def start(self):
        """Запускает бота."""
        try:
            application = Application.builder().token(self.bot_token).build()
            
            # Добавляем обработчики команд
            application.add_handler(CommandHandler("start", self.cmd_start))
            application.add_handler(CommandHandler("help", self.cmd_help))
            
            # Обработчик видео файлов
            application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, self.handle_video))
            
            # Обработчик видео файлов, отправленных как документы
            application.add_handler(MessageHandler(
                filters.Document.MimeType("video/mp4") | 
                filters.Document.MimeType("video/quicktime") | 
                filters.Document.MimeType("video/x-matroska") | 
                filters.Document.MimeType("video/webm"), 
                self.handle_video_document
            ))
            
            # Обработчик YouTube ссылок
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Запускаем бота
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            
            logger.info("Бот запущен и ожидает сообщений")
            
            # Держим бота запущенным
            self.is_running = True
            while self.is_running:
                await asyncio.sleep(1)
                
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise
    
    async def stop(self):
        """Останавливает бота."""
        self.is_running = False
        logger.info("Получена команда на остановку бота")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /start."""
        if not self._is_user_authorized(update):
            return
        
        await update.message.reply_text(
            "👋 Привет! Я бот для саммаризации видео.\n\n"
            "📤 Отправь мне видео файл или ссылку на YouTube видео, и я сделаю его краткое содержание.\n\n"
            "🔍 Для YouTube видео я использую субтитры, для обычных видео - анализирую аудиодорожку.\n\n"
            "⚡️ Для получения помощи используй команду /help"
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает команду /help."""
        if not self._is_user_authorized(update):
            return
        
        await update.message.reply_text(
            "📚 Помощь по использованию бота:\n\n"
            "1. Для анализа YouTube видео - просто отправь ссылку\n"
            "2. Для анализа видеофайла - отправь его как видео или документ\n\n"
            "⚠️ Обратите внимание:\n"
            "- Размер видеофайла не должен превышать 20 МБ\n"
            "- Обработка может занять некоторое время, в зависимости от длины видео\n"
            "- Для YouTube видео необходимы субтитры (автоматические также поддерживаются)\n\n"
            "Если возникли проблемы, свяжитесь с разработчиком."
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает текстовые сообщения для извлечения YouTube URL."""
        if not self._is_user_authorized(update):
            return
        
        message_text = update.message.text
        
        # Проверяем, есть ли в сообщении YouTube ссылка
        youtube_match = re.search(YOUTUBE_URL_PATTERN, message_text)
        if youtube_match:
            youtube_url = youtube_match.group(0)
            
            # Отправляем сообщение о начале обработки
            await update.message.reply_text(f"🔍 Начинаю обработку YouTube видео: {youtube_url}\nПожалуйста, подождите...")
            
            try:
                # Обрабатываем YouTube ссылку
                result = await self.video_processor.process_youtube_url(youtube_url)
                
                # Отправляем результат
                await self._send_video_summary(update, result)
                
            except Exception as e:
                logger.error(f"Ошибка при обработке YouTube URL: {e}")
                await update.message.reply_text(f"❌ Не удалось обработать YouTube видео: {str(e)}")
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает видео, отправленные как видео."""
        if not self._is_user_authorized(update):
            return
        
        await update.message.reply_text("🎬 Получил видео! Начинаю обработку, это может занять некоторое время...")
        
        try:
            # Скачиваем видео
            video_file = await update.message.video.get_file()
            
            # Создаем временный файл для видео
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                video_path = tmp_file.name
            
            # Загружаем видео во временный файл
            await video_file.download_to_drive(video_path)
            logger.info(f"Видео загружено в {video_path}")
            
            # Обрабатываем видео
            result = await self.video_processor.process_video_file(video_path)
            
            # Отправляем результат
            await self._send_video_summary(update, result)
            
            # Удаляем временный файл
            os.remove(video_path)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео: {e}")
            await update.message.reply_text(f"❌ Не удалось обработать видео: {str(e)}")
    
    async def handle_video_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает видео, отправленные как документы."""
        if not self._is_user_authorized(update):
            return
        
        await update.message.reply_text("🎬 Получил видео! Начинаю обработку, это может занять некоторое время...")
        
        try:
            # Скачиваем видео
            video_file = await update.message.document.get_file()
            
            # Создаем временный файл для видео
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                video_path = tmp_file.name
            
            # Загружаем видео во временный файл
            await video_file.download_to_drive(video_path)
            logger.info(f"Видео загружено в {video_path}")
            
            # Обрабатываем видео
            result = await self.video_processor.process_video_file(video_path)
            
            # Отправляем результат
            await self._send_video_summary(update, result)
            
            # Удаляем временный файл
            os.remove(video_path)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео: {e}")
            await update.message.reply_text(f"❌ Не удалось обработать видео: {str(e)}")
    
    async def _send_video_summary(self, update: Update, result: Dict[str, Any]):
        """
        Отправляет саммари и транскрипцию видео.
        
        Args:
            update (Update): Объект обновления Telegram
            result (Dict[str, Any]): Результат обработки видео
        """
        summary = result.get("summary", "")
        transcript = result.get("transcript", "")
        
        # Отправляем саммари
        await update.message.reply_text(f"📝 Вот саммари видео:\n\n{summary}")
        
        # Если транскрипция слишком длинная, отправляем её частями
        if len(transcript) > 4000:
            parts = [transcript[i:i+4000] for i in range(0, len(transcript), 4000)]
            for i, part in enumerate(parts):
                await update.message.reply_text(f"📄 Транскрипция (часть {i+1}/{len(parts)}):\n\n{part}")
        else:
            await update.message.reply_text(f"📄 Полная транскрипция:\n\n{transcript}")
    
    def _is_user_authorized(self, update: Update) -> bool:
        """
        Проверяет, авторизован ли пользователь для использования бота.
        
        Args:
            update (Update): Объект обновления Telegram
            
        Returns:
            bool: True, если пользователь авторизован, иначе False
        """
        user_id = update.effective_user.id
        if not self.authorized_user_ids or user_id in self.authorized_user_ids:
            return True
        
        logger.warning(f"Неавторизованная попытка доступа от пользователя {user_id}")
        update.message.reply_text("⛔ У вас нет доступа к этому боту.")
        return False 