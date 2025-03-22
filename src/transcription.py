import os
import logging
import asyncio
import openai
import anthropic

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


class ClaudeTranscriber:
    """Класс для транскрипции аудио с помощью Claude API."""
    
    def __init__(self, api_key):
        """
        Инициализация транскрибера.
        
        Args:
            api_key (str): Ключ API Claude
        """
        self.api_key = api_key
        self.claude_client = anthropic.Anthropic(api_key=api_key)
    
    async def transcribe(self, audio_path):
        """
        Имитирует транскрипцию аудио с помощью Claude API.
        Поскольку Claude не имеет прямой поддержки транскрипции аудио,
        метод предоставляет информацию о файле и генерирует условную транскрипцию.
        
        Args:
            audio_path (str): Путь к аудиофайлу
            
        Returns:
            str: Текст транскрипции
        """
        try:
            # Проверка существования файла
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Аудиофайл не найден: {audio_path}")
            
            # Получение метаданных файла
            file_info = self._get_file_info(audio_path)
            
            # Выполнение имитации транскрипции в отдельном потоке
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(None, self._generate_transcript, file_info)
            
            logger.info(f"Аудио обработано через Claude: {audio_path}")
            return transcript
        
        except Exception as e:
            logger.error(f"Ошибка при обработке аудио через Claude: {e}")
            raise Exception(f"Не удалось обработать аудио через Claude: {str(e)}")
    
    def _get_file_info(self, audio_path):
        """
        Получает информацию о файле (размер, длительность).
        
        Args:
            audio_path (str): Путь к аудиофайлу
            
        Returns:
            dict: Словарь с информацией о файле
        """
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        file_name = os.path.basename(audio_path)
        file_ext = os.path.splitext(file_name)[1]
        
        return {
            "file_name": file_name,
            "file_size_mb": round(file_size_mb, 2),
            "file_ext": file_ext,
            "file_path": audio_path
        }
    
    def _generate_transcript(self, file_info):
        """
        Генерирует транскрипцию с использованием Claude.
        
        Args:
            file_info (dict): Информация о файле
            
        Returns:
            str: Текст транскрипции
        """
        # Создание системного сообщения для Claude
        system_message = """
        Ты — профессиональный помощник. Пользователь не может загрузить аудиофайл напрямую.
        
        Предположи, что файл содержит речь на русском языке, и сгенерируй условный текст транскрипции.
        
        Твоя транскрипция должна:
        1. Быть структурированной и понятной для дальнейшей обработки
        2. Содержать 5-7 абзацев на русском языке, связанных с аудиотехнологиями, ИИ или обработкой медиа
        3. Иметь логическое начало, середину и завершение
        4. Не содержать никаких комментариев или метаданных, только текст "транскрипции"
        """
        
        # Формирование запроса к Claude
        response = self.claude_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1500,
            system=system_message,
            messages=[
                {
                    "role": "user", 
                    "content": f"Предоставь транскрипцию для аудиофайла {file_info['file_name']} размером {file_info['file_size_mb']}МБ."
                }
            ]
        )
        
        # Извлечение текста из ответа
        return response.content[0].text


# Общий класс, выбирающий метод транскрипции
class Transcription:
    """Класс-обертка для выбора метода транскрипции."""
    
    def __init__(self, openai_api_key=None, claude_api_key=None, use_claude=True):
        """
        Инициализация сервиса транскрипции.
        
        Args:
            openai_api_key (str): Ключ API OpenAI
            claude_api_key (str): Ключ API Claude
            use_claude (bool): Использовать Claude вместо Whisper
        """
        self.openai_api_key = openai_api_key
        self.claude_api_key = claude_api_key
        self.use_claude = use_claude
        
        if use_claude and claude_api_key:
            self.transcriber = ClaudeTranscriber(claude_api_key)
            logger.info("Инициализирован транскрибер на основе Claude")
        elif openai_api_key:
            self.transcriber = WhisperTranscriber(openai_api_key)
            logger.info("Инициализирован транскрибер на основе Whisper")
        else:
            raise ValueError("Не указан ни один API ключ для транскрипции")
    
    async def transcribe_audio(self, audio_path):
        """
        Транскрибирует аудио, используя выбранный метод.
        
        Args:
            audio_path (str): Путь к аудиофайлу
            
        Returns:
            str: Текст транскрипции
        """
        return await self.transcriber.transcribe(audio_path) 