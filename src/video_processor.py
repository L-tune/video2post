import os
import logging
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

logger = logging.getLogger(__name__)

# Паттерн для извлечения ID видео из YouTube URL
YOUTUBE_URL_PATTERN = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'

class VideoProcessor:
    """Класс для обработки видеофайлов и YouTube URL."""
    
    def __init__(self, temp_folder, proxy=None):
        """
        Инициализация процессора видео.
        
        Args:
            temp_folder (str): Путь к временной директории для хранения файлов
            proxy (str, optional): Прокси-сервер для запросов к YouTube API (формат: http://user:pass@host:port)
        """
        self.temp_folder = temp_folder
        self.proxy = proxy
        
        if proxy:
            logger.info(f"Инициализирован VideoProcessor с прокси")
        else:
            logger.info("Инициализирован VideoProcessor без прокси")

    async def process_youtube_url(self, youtube_url):
        """
        Обрабатывает YouTube URL, извлекая субтитры через API или прокси.
        
        Args:
            youtube_url (str): URL видео на YouTube
            
        Returns:
            dict: Словарь с информацией о видео и транскрипцией
        """
        try:
            # Проверка и очистка URL
            video_id = self._extract_video_id(youtube_url)
            if not video_id:
                raise ValueError(f"Не удалось извлечь ID видео из URL: {youtube_url}")
            
            logger.info(f"Обработка YouTube видео с ID: {video_id}")
            
            # Сначала пробуем через прокси, если он есть
            if self.proxy:
                try:
                    logger.info(f"Попытка получения субтитров через прокси")
                    result = await self._get_subtitles_via_proxy(video_id)
                    return result
                except Exception as proxy_e:
                    logger.error(f"Не удалось получить субтитры через прокси: {proxy_e}")
            
            # Если нет прокси или он не сработал, пробуем напрямую
            logger.info(f"Получение субтитров напрямую для видео {video_id}")
            return await self._get_subtitles_via_api(video_id)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке YouTube URL: {e}")
            raise

    async def _get_subtitles_via_api(self, video_id):
        """
        Получает субтитры через YouTube Transcript API.
        
        Args:
            video_id (str): ID видео на YouTube
            
        Returns:
            dict: Словарь с информацией о видео и транскрипцией
        """
        try:
            # Пытаемся вывести список доступных транскриптов
            available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            logger.info(f"Доступные транскрипты: {', '.join([f'{t.language} ({t.language_code})' for t in available_transcripts._transcripts.values()])}")
            
            # Сначала пробуем получить русские субтитры
            try:
                logger.info("Попытка получить русские субтитры")
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru'])
                logger.info(f"Получены русские субтитры, {len(transcript_list)} сегментов")
            except (NoTranscriptFound, TranscriptsDisabled) as e:
                logger.info(f"Русские субтитры недоступны: {e}, пробуем английские")
                # Если русские недоступны, пробуем английские
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                logger.info(f"Получены английские субтитры, {len(transcript_list)} сегментов")
        
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {e}")
            logger.info("Попытка получить автоматически созданные транскрипты")
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                logger.info(f"Получены автоматические субтитры, {len(transcript)} сегментов")
                transcript_list = transcript
            except Exception as nested_e:
                logger.error(f"Не удалось получить субтитры: {nested_e}")
                raise Exception(f"Не удалось получить субтитры для видео: {str(nested_e)}")
        
        # Объединение текста субтитров
        transcription = " ".join([item['text'] for item in transcript_list])
        
        return {
            'video_id': video_id,
            'transcription': transcription,
            'transcript_segments': transcript_list
        }
    
    async def _get_subtitles_via_proxy(self, video_id):
        """
        Получает субтитры через прокси-сервер.
        
        Args:
            video_id (str): ID видео на YouTube
            
        Returns:
            dict: Словарь с информацией о видео и транскрипцией
        """
        try:
            # Формируем прокси для библиотеки
            proxies = {'http': self.proxy, 'https': self.proxy}
            
            # Пробуем получить список доступных транскриптов через прокси
            available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id, proxies=proxies)
            available_langs = [f'{t.language} ({t.language_code})' for t in available_transcripts._transcripts.values()]
            logger.info(f"Доступные через прокси транскрипты: {', '.join(available_langs)}")
            
            # Пробуем русские субтитры через прокси
            try:
                logger.info("Попытка получить русские субтитры через прокси")
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru'], proxies=proxies)
                logger.info(f"Получены русские субтитры через прокси, {len(transcript_list)} сегментов")
            except (NoTranscriptFound, TranscriptsDisabled) as e:
                logger.info(f"Русские субтитры недоступны через прокси: {e}, пробуем английские")
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'], proxies=proxies)
                logger.info(f"Получены английские субтитры через прокси, {len(transcript_list)} сегментов")
            
            # Объединение текста субтитров
            transcription = " ".join([item['text'] for item in transcript_list])
            
            return {
                'video_id': video_id,
                'transcription': transcription,
                'transcript_segments': transcript_list,
                'source': 'proxy'
            }
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров через прокси: {e}")
            raise Exception(f"Не удалось получить субтитры через прокси: {str(e)}")
    
    def _extract_video_id(self, youtube_url):
        """
        Извлекает ID видео из YouTube URL.
        
        Args:
            youtube_url (str): URL видео на YouTube
            
        Returns:
            str: ID видео или None, если ID не найден
        """
        match = re.search(YOUTUBE_URL_PATTERN, youtube_url)
        if match:
            return match.group(6)
        return None 