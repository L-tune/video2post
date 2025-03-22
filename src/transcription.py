import os
import logging
import asyncio
import openai

logger = logging.getLogger(__name__)

class WhisperTranscriber:
    """Класс для транскрипции аудио с помощью OpenAI Whisper API."""
    
    def __init__(self, api_key):
        """
        Инициализация транскрибера.
        
        Args:
            api_key (str): Ключ API OpenAI
        """
        self.api_key = api_key
        openai.api_key = api_key
    
    async def transcribe(self, audio_path):
        """
        Транскрибирует аудио с помощью Whisper API.
        
        Args:
            audio_path (str): Путь к аудиофайлу
            
        Returns:
            str: Текст транскрипции
        """
        try:
            # Проверка существования файла
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Аудиофайл не найден: {audio_path}")
            
            # Проверка размера файла (не более 25 МБ для API)
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            if file_size_mb > 25:
                raise ValueError(f"Размер файла ({file_size_mb:.2f} МБ) превышает лимит в 25 МБ для Whisper API")
            
            # Выполнение транскрипции в отдельном потоке
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(None, self._transcribe_sync, audio_path)
            
            logger.info(f"Аудио успешно транскрибировано: {audio_path}")
            return transcript
        
        except Exception as e:
            logger.error(f"Ошибка при транскрибации аудио: {e}")
            raise Exception(f"Не удалось транскрибировать аудио: {str(e)}")
    
    def _transcribe_sync(self, audio_path):
        """
        Синхронный метод для транскрипции аудио.
        
        Args:
            audio_path (str): Путь к аудиофайлу
            
        Returns:
            str: Текст транскрипции
        """
        with open(audio_path, "rb") as audio_file:
            # Выполнение запроса к Whisper API
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru",
                response_format="text"
            )
            
            # В API V1 результат возвращается напрямую как строка
            return response 