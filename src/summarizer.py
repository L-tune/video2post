import logging
import asyncio
import json
import os
import re
from typing import Dict, Any, Optional, List
from anthropic import Anthropic
from src.youtube_subtitles import YouTubeSubtitlesExtractor
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class Summarizer:
    """Класс для создания саммари из субтитров YouTube видео."""
    
    def __init__(self, youtube_api_key: str, claude_api_key: str):
        """
        Инициализация саммарайзера.
        
        Args:
            youtube_api_key (str): API ключ для YouTube Data API
            claude_api_key (str): API ключ для Claude API
        """
        self.youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        self.claude = Anthropic(api_key=claude_api_key)
        logger.info("Summarizer: Инициализирован")
        
    def _extract_video_id(self, url: str) -> str:
        """
        Извлекает ID видео из YouTube URL
        
        Args:
            url (str): URL YouTube видео
            
        Returns:
            str: ID видео
        """
        # Поддерживаемые форматы:
        # - https://www.youtube.com/watch?v=VIDEO_ID
        # - https://youtu.be/VIDEO_ID
        # - https://www.youtube.com/embed/VIDEO_ID
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
            r'(?:embed\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
        raise ValueError(f"Не удалось извлечь ID видео из URL: {url}")
        
    async def _get_video_info(self, video_id: str) -> Dict[str, str]:
        """
        Получает информацию о видео через YouTube API
        
        Args:
            video_id (str): ID видео
            
        Returns:
            Dict[str, str]: Словарь с информацией о видео
        """
        try:
            response = self.youtube.videos().list(
                part='snippet',
                id=video_id
            ).execute()
            
            if not response['items']:
                raise ValueError(f"Видео с ID {video_id} не найдено")
                
            snippet = response['items'][0]['snippet']
            return {
                'title': snippet['title'],
                'description': snippet['description']
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о видео: {e}")
            raise
            
    async def _get_transcript(self, video_id: str) -> str:
        """
        Получает транскрипцию видео
        
        Args:
            video_id (str): ID видео
            
        Returns:
            str: Текст транскрипции
        """
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru', 'en'])
            return ' '.join(item['text'] for item in transcript_list)
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции: {e}")
            raise
            
    async def _generate_summary(self, title: str, transcript: str) -> str:
        """
        Генерирует саммари с помощью Claude
        
        Args:
            title (str): Название видео
            transcript (str): Текст транскрипции
            
        Returns:
            str: Сгенерированное саммари
        """
        try:
            prompt = f"""Ты - эксперт по созданию кратких и информативных саммари. 
            Тебе нужно создать краткое и структурированное саммари для видео.
            
            Название видео: {title}
            
            Транскрипция:
            {transcript}
            
            Пожалуйста, создай краткое (не более 2000 символов) и информативное саммари этого видео.
            Саммари должно:
            1. Отражать основные идеи и ключевые моменты
            2. Быть структурированным и легко читаемым
            3. Не содержать лишних деталей
            4. Сохранять логическую последовательность изложения
            
            Формат:
            - Краткое описание (1-2 предложения)
            - Основные темы/пункты
            - Ключевые выводы (если есть)
            """
            
            response = self.claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Ошибка при генерации саммари: {e}")
            raise
            
    async def generate_summary(self, youtube_url: str) -> Optional[Dict[str, Any]]:
        """
        Генерирует саммари для YouTube видео
        
        Args:
            youtube_url (str): URL YouTube видео
            
        Returns:
            Optional[Dict[str, Any]]: Результат с саммари и дополнительной информацией
        """
        try:
            # Извлекаем ID видео
            video_id = self._extract_video_id(youtube_url)
            logger.info(f"Извлечен ID видео: {video_id}")
            
            # Получаем информацию о видео
            video_info = await self._get_video_info(video_id)
            logger.info(f"Получена информация о видео: {video_info['title']}")
            
            # Получаем транскрипцию
            transcript = await self._get_transcript(video_id)
            logger.info(f"Получена транскрипция длиной {len(transcript)} символов")
            
            # Генерируем саммари
            summary = await self._generate_summary(video_info['title'], transcript)
            logger.info(f"Сгенерировано саммари длиной {len(summary)} символов")
            
            return {
                "video_id": video_id,
                "video_title": video_info['title'],
                "video_description": video_info['description'],
                "transcript": transcript,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Ошибка при генерации саммари: {e}")
            return None 