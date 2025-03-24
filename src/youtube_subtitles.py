import logging
import asyncio
import re
import os
import requests
import xml.etree.ElementTree as ET
import json
import subprocess
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

class YouTubeSubtitlesExtractor:
    """Класс для извлечения субтитров из YouTube видео."""
    
    def __init__(self):
        """
        Инициализация экстрактора субтитров.
        """
        logger.info("YouTubeSubtitlesExtractor: Инициализирован")

    def extract_video_id(self, youtube_url):
        """
        Извлекает ID видео из YouTube URL.
        
        Args:
            youtube_url (str): URL YouTube видео
            
        Returns:
            str: ID видео или None, если ID не найден
        """
        # Шаблоны для разных форматов YouTube URL
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\?\/]+)',
            r'youtube\.com\/shorts\/([^&\?\/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                return match.group(1)
        
        return None
    
    async def get_subtitles(self, youtube_url: str) -> Dict[str, Any]:
        """
        Получает субтитры из YouTube видео.
        
        Args:
            youtube_url (str): URL YouTube видео
            
        Returns:
            Dict[str, Any]: Словарь с результатами:
                - transcript: Полный текст субтитров
                - video_title: Название видео
                - video_id: ID видео
        """
        try:
            # Извлекаем ID видео из URL
            video_id = self._extract_video_id(youtube_url)
            if not video_id:
                logger.error(f"Не удалось извлечь ID видео из URL: {youtube_url}")
                raise ValueError(f"Неверная ссылка на YouTube видео: {youtube_url}")
            
            logger.info(f"Получен ID видео: {video_id}")
            
            # Получаем информацию о видео
            video_info = await self._get_video_info(video_id)
            video_title = video_info.get("title", "")
            
            logger.info(f"Название видео: {video_title}")
            
            # Получаем субтитры
            transcript_text = await self._get_transcript(video_id)
            
            if not transcript_text:
                logger.warning(f"Не удалось получить субтитры для видео {video_id}")
                return {
                    "transcript": "",
                    "video_title": video_title,
                    "video_id": video_id
                }
            
            logger.info(f"Получены субтитры длиной {len(transcript_text)} символов")
            
            return {
                "transcript": transcript_text,
                "video_title": video_title,
                "video_id": video_id
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {e}")
            raise Exception(f"Не удалось получить субтитры: {str(e)}")
    
    def _extract_video_id(self, youtube_url: str) -> str:
        """
        Извлекает ID видео из YouTube URL.
        
        Args:
            youtube_url (str): URL YouTube видео
            
        Returns:
            str: ID видео или пустая строка, если ID не найден
        """
        try:
            # Паттерн для извлечения ID видео
            pattern = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
            match = re.search(pattern, youtube_url)
            
            if match:
                return match.group(1)
            
            return ""
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении ID видео: {e}")
            return ""
    
    async def _get_video_info(self, video_id: str) -> Dict[str, Any]:
        """
        Получает информацию о видео с помощью yt-dlp.
        
        Args:
            video_id (str): ID видео
            
        Returns:
            Dict[str, Any]: Информация о видео
        """
        try:
            # Запускаем yt-dlp для получения информации о видео
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp", f"https://www.youtube.com/watch?v={video_id}", 
                "--dump-json", "--no-playlist", "--skip-download",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"Ошибка при получении информации о видео: {stderr.decode()}")
                return {"title": ""}
            
            # Парсим JSON из вывода yt-dlp
            video_info = json.loads(stdout.decode())
            return video_info
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о видео: {e}")
            return {"title": ""}
    
    async def _get_transcript(self, video_id: str) -> str:
        """
        Получает субтитры из видео.
        
        Args:
            video_id (str): ID видео
            
        Returns:
            str: Текст субтитров или пустая строка, если субтитры недоступны
        """
        try:
            # Запускаем получение субтитров в отдельном потоке
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None,
                lambda: self._get_transcript_sync(video_id)
            )
            
            return transcript
            
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {e}")
            return ""
    
    def _get_transcript_sync(self, video_id: str) -> str:
        """
        Синхронно получает субтитры с помощью youtube_transcript_api.
        
        Args:
            video_id (str): ID видео
            
        Returns:
            str: Текст субтитров или пустая строка, если субтитры недоступны
        """
        try:
            # Пытаемся получить субтитры
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Сначала пытаемся найти русские субтитры
            try:
                transcript = transcript_list.find_transcript(['ru'])
                logger.info("Найдены русские субтитры")
            except NoTranscriptFound:
                # Если русских нет, берем любые доступные
                transcript = transcript_list.find_transcript(['en'])
                logger.info("Найдены английские субтитры")
                # Переводим субтитры на русский
                transcript = transcript.translate('ru')
                logger.info("Субтитры переведены на русский")
            
            # Получаем текст субтитров
            transcript_data = transcript.fetch()
            
            # Объединяем все фрагменты субтитров в один текст
            transcript_text = " ".join([item['text'] for item in transcript_data])
            
            return transcript_text
            
        except TranscriptsDisabled:
            logger.warning(f"Субтитры отключены для видео {video_id}")
            return ""
        except NoTranscriptFound:
            logger.warning(f"Не найдены субтитры для видео {video_id}")
            return ""
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {e}")
            return "" 