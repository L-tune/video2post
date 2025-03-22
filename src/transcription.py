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
        Транскрибирует аудио с помощью Claude API.
        
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
                raise ValueError(f"Размер файла ({file_size_mb:.2f} МБ) превышает лимит для Claude API")
            
            # Выполнение транскрипции в отдельном потоке
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(None, self._transcribe_sync, audio_path)
            
            logger.info(f"Аудио успешно транскрибировано через Claude: {audio_path}")
            return transcript
        
        except Exception as e:
            logger.error(f"Ошибка при транскрибации аудио через Claude: {e}")
            raise Exception(f"Не удалось транскрибировать аудио через Claude: {str(e)}")
    
    def _transcribe_sync(self, audio_path):
        """
        Синхронный метод для транскрипции аудио через Claude.
        
        Args:
            audio_path (str): Путь к аудиофайлу
            
        Returns:
            str: Текст транскрипции
        """
        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()
            
            # Создание системного сообщения для Claude
            system_message = """
            Ты — профессиональный транскрибер. Твоя задача — точно преобразовать аудио в текст.
            Сохраняй все произнесенные слова, включая слова-паразиты, повторения и оговорки.
            Учитывай тон, интонацию и паузы, если они значимы для понимания текста.
            Текст должен быть разбит на логические абзацы.
            Язык ответа: русский.
            """
            
            # Формирование запроса к Claude с аудиофайлом в формате base64
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4000,
                system=system_message,
                messages=[
                    {
                        "role": "user", 
                        "content": f"Пожалуйста, сделай подробную транскрипцию этого аудиофайла. Только текст, без анализа."
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