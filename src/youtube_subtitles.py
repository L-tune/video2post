import logging
import asyncio
import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from openai import OpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class YouTubeSubtitlesExtractor:
    """Класс для извлечения субтитров из YouTube видео и их обработки."""
    
    def __init__(self, openai_api_key, claude_api_key=None, use_claude=False):
        """
        Инициализация экстрактора субтитров.
        
        Args:
            openai_api_key (str): Ключ API OpenAI
            claude_api_key (str, optional): Ключ API Claude
            use_claude (bool): Использовать Claude вместо OpenAI
        """
        self.use_claude = use_claude
        
        if use_claude and claude_api_key:
            logger.info(f"YouTubeSubtitlesExtractor: Используем Claude API, ключ: {claude_api_key[:10]}...")
            self.api_key = claude_api_key
            
            try:
                self.client = Anthropic(api_key=claude_api_key)
                logger.info("YouTubeSubtitlesExtractor: Клиент Claude успешно создан")
            except Exception as e:
                logger.error(f"YouTubeSubtitlesExtractor: Ошибка при создании клиента Claude: {e}")
                raise
        else:
            logger.info(f"YouTubeSubtitlesExtractor: Используем OpenAI API, ключ: {openai_api_key[:10]}...")
            self.api_key = openai_api_key
            
            try:
                self.client = OpenAI(api_key=openai_api_key)
                logger.info("YouTubeSubtitlesExtractor: Клиент OpenAI успешно создан")
            except Exception as e:
                logger.error(f"YouTubeSubtitlesExtractor: Ошибка при создании клиента OpenAI: {e}")
                raise
    
    def extract_video_id(self, youtube_url):
        """
        Извлекает ID видео из YouTube URL.
        
        Args:
            youtube_url (str): URL YouTube видео
            
        Returns:
            str: ID видео или None, если URL некорректный
        """
        try:
            # Регулярное выражение для поиска ID видео в различных форматах URL
            patterns = [
                r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([^&\n?#]+)',
                r'youtube\.com\/embed\/([^&\n?#]+)',
                r'youtube\.com\/v\/([^&\n?#]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, youtube_url)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            logger.error(f"Ошибка при извлечении ID видео: {e}")
            return None
    
    async def get_subtitles(self, youtube_url, preferred_lang='ru'):
        """
        Получает субтитры из YouTube видео.
        
        Args:
            youtube_url (str): URL YouTube видео
            preferred_lang (str): Предпочтительный язык субтитров
            
        Returns:
            str: Текст субтитров или None, если субтитры недоступны
        """
        try:
            video_id = self.extract_video_id(youtube_url)
            if not video_id:
                raise ValueError(f"Не удалось извлечь ID видео из URL: {youtube_url}")
                
            logger.info(f"Получен ID видео: {video_id}")
            
            # Запуск в отдельном потоке, так как YouTube API блокирующий
            loop = asyncio.get_event_loop()
            transcript_text = await loop.run_in_executor(
                None,
                lambda: self._get_subtitles_sync(video_id, preferred_lang)
            )
            
            return transcript_text
            
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {e}")
            raise
    
    def _get_subtitles_sync(self, video_id, preferred_lang='ru'):
        """
        Синхронный метод для получения субтитров.
        
        Args:
            video_id (str): ID YouTube видео
            preferred_lang (str): Предпочтительный язык субтитров
            
        Returns:
            str: Текст субтитров
        """
        try:
            # Получение списка доступных субтитров
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Пытаемся получить субтитры на предпочтительном языке
            try:
                transcript = transcript_list.find_transcript([preferred_lang])
            except NoTranscriptFound:
                # Если субтитры на предпочтительном языке не найдены,
                # пытаемся получить субтитры на английском
                try:
                    transcript = transcript_list.find_transcript(['en'])
                except NoTranscriptFound:
                    # Если субтитры на английском не найдены,
                    # берем первый доступный язык
                    transcript = transcript_list.find_transcript([])
            
            # Получение текста субтитров
            transcript_data = transcript.fetch()
            
            # Формирование полного текста из субтитров
            full_text = ' '.join([item['text'] for item in transcript_data])
            
            return full_text
            
        except TranscriptsDisabled:
            raise Exception("Субтитры для этого видео отключены")
        except NoTranscriptFound:
            raise Exception("Субтитры для этого видео не найдены")
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {e}")
            raise
    
    async def generate_summary(self, subtitle_text):
        """
        Генерирует саммари с ключевыми фактами из субтитров.
        
        Args:
            subtitle_text (str): Текст субтитров
            
        Returns:
            str: Саммари с ключевыми фактами
        """
        try:
            # Обрезаем текст, если он слишком длинный
            max_tokens = 12000
            if len(subtitle_text) > max_tokens:
                subtitle_text = subtitle_text[:16000] + "...[текст субтитров был обрезан из-за ограничений]"
            
            # Выполнение запроса к модели в отдельном потоке
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(
                None, 
                lambda: self._generate_summary_sync(subtitle_text)
            )
            
            logger.info("Саммари успешно сгенерировано")
            return summary
        
        except Exception as e:
            logger.error(f"Ошибка при генерации саммари: {e}")
            raise Exception(f"Не удалось сгенерировать саммари: {str(e)}")
    
    def _generate_summary_sync(self, subtitle_text):
        """
        Синхронный метод для генерации саммари.
        
        Args:
            subtitle_text (str): Текст субтитров
            
        Returns:
            str: Саммари с ключевыми фактами
        """
        try:
            logger.info("Начинаю генерацию саммари из субтитров...")
            
            # Системный промпт для определения задачи
            system_prompt = """Ты эксперт по анализу текста. Тебе нужно проанализировать субтитры видео и выделить из них ключевые факты и идеи.

Твоя задача:
1. Выделить 5-7 ключевых фактов или идей из субтитров
2. Коротко структурировать их в формате маркированного списка
3. Сохранить важные числа, имена, цитаты и технические детали
4. Обеспечить, чтобы полученное саммари отражало суть контента без потери важной информации

Представь результат в формате:

КЛЮЧЕВЫЕ ФАКТЫ:
• [Факт 1]
• [Факт 2]
• [Факт 3]
...

ОСНОВНЫЕ ВЫВОДЫ:
[1-2 предложения с главными выводами из видео]

Пиши только на русском языке."""
            
            if self.use_claude:
                # Запрос к Claude
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=1000,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": f"Вот субтитры YouTube видео, которые нужно анализировать:\n\n{subtitle_text}"}
                    ]
                )
                # Извлечение сгенерированного текста
                return response.content[0].text
            else:
                # Запрос к GPT-4o
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Вот субтитры YouTube видео, которые нужно анализировать:\n\n{subtitle_text}"}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                # Извлечение сгенерированного текста
                return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Ошибка при генерации саммари: {e}")
            raise Exception(f"Не удалось сгенерировать саммари: {str(e)}") 