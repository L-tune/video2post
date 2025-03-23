import os
import logging
import asyncio
from openai import OpenAI

logger = logging.getLogger(__name__)

class WhisperTranscriber:
    """Класс для транскрипции аудио с помощью OpenAI Whisper API."""
    
    def __init__(self, api_key):
        """
        Инициализация транскрибера.
        
        Args:
            api_key (str): Ключ API OpenAI
        """
        logger.info(f"WhisperTranscriber: Получен ключ API: {api_key[:10]}...")
        
        # Проверка на пустой или неверный ключ
        if not api_key or api_key == "OPENAI_API_KEY" or not isinstance(api_key, str):
            error_msg = f"WhisperTranscriber: Некорректный ключ API: {type(api_key)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.api_key = api_key
        
        # Создание клиента OpenAI с явным указанием ключа API
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("WhisperTranscriber: Клиент OpenAI успешно создан")
        except Exception as e:
            logger.error(f"WhisperTranscriber: Ошибка при создании клиента OpenAI: {e}")
            raise
    
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
        try:
            logger.info(f"Начинаю транскрипцию аудио: {audio_path}")
            logger.info(f"Использую API ключ: {self.api_key[:10]}...")
            
            with open(audio_path, "rb") as audio_file:
                # Выполнение запроса к Whisper API
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru",
                    response_format="text"
                )
                
                logger.info("Транскрипция успешно выполнена")
                # В API V1 результат возвращается напрямую как строка
                return response
        except Exception as e:
            logger.error(f"Ошибка в _transcribe_sync: {e}")
            raise 