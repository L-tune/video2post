import logging
import os
import tempfile
from typing import Optional, Tuple, Dict, Any
import subprocess
import asyncio
from moviepy.editor import VideoFileClip

from src.youtube_subtitles import YouTubeSubtitlesExtractor

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Класс для обработки видео файлов и получения саммари."""
    
    def __init__(self, openai_api_key: str = None, temp_folder: str = None, proxy: str = None):
        """
        Инициализация процессора видео.
        
        Args:
            openai_api_key (str, optional): API ключ OpenAI (необходим для саммаризации)
            temp_folder (str, optional): Путь к временной директории для хранения файлов
            proxy (str, optional): Прокси-сервер для запросов к YouTube API (формат: host:port:username:password)
        """
        self.openai_api_key = openai_api_key
        self.temp_folder = temp_folder or tempfile.mkdtemp()
        self.proxy = proxy
        
        if openai_api_key:
            from src.summarizer import VideoSummarizer
            self.summarizer = VideoSummarizer(api_key=openai_api_key)
        else:
            self.summarizer = None
        
        self.youtube_extractor = YouTubeSubtitlesExtractor(proxy=proxy)
        
        if proxy:
            logger.info(f"VideoProcessor: Инициализирован с прокси")
        else:
            logger.info("VideoProcessor: Инициализирован")
    
    async def process_video_file(self, video_path: str) -> Dict[str, Any]:
        """
        Обрабатывает видеофайл и возвращает саммари и транскрипцию.
        
        Args:
            video_path (str): Путь к видеофайлу
            
        Returns:
            Dict[str, Any]: Словарь с результатами обработки:
                - transcript: текст транскрипции
                - summary: саммари видео
                - duration: длительность видео в секундах
        """
        try:
            logger.info(f"Начинаю обработку видео файла: {video_path}")
            
            # Извлекаем аудио из видео
            audio_path = await self._extract_audio(video_path)
            logger.info(f"Аудио извлечено в: {audio_path}")
            
            # Получаем транскрипцию
            transcript = await self._get_transcription(audio_path)
            logger.info(f"Получена транскрипция длиной {len(transcript)} символов")
            
            # Удаляем временный аудиофайл
            os.remove(audio_path)
            
            # Получаем длительность видео
            duration = self._get_video_duration(video_path)
            
            # Получаем саммари
            summary = await self.summarizer.summarize(transcript)
            logger.info(f"Получено саммари длиной {len(summary)} символов")
            
            return {
                "transcript": transcript,
                "summary": summary,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео файла: {e}")
            raise
    
    async def process_youtube_url(self, youtube_url: str) -> Dict[str, Any]:
        """
        Обрабатывает YouTube URL и возвращает транскрипцию.
        
        Args:
            youtube_url (str): Ссылка на YouTube видео
            
        Returns:
            Dict[str, Any]: Словарь с результатами обработки:
                - transcript: текст транскрипции
                - video_title: название видео
                - video_id: ID видео
                - video_url: URL видео
        """
        try:
            logger.info(f"Начинаю обработку YouTube URL: {youtube_url}")
            
            # Получаем субтитры и метаданные
            subtitle_result = await self.youtube_extractor.get_subtitles(youtube_url)
            if not subtitle_result["transcript"]:
                raise Exception("Не удалось получить субтитры для данного видео")
            
            transcript = subtitle_result["transcript"]
            logger.info(f"Получена транскрипция длиной {len(transcript)} символов")
            
            return {
                "transcript": transcript,
                "video_title": subtitle_result.get("video_title", ""),
                "video_id": subtitle_result.get("video_id", ""),
                "video_url": youtube_url
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обработке YouTube URL: {e}")
            raise
    
    async def _extract_audio(self, video_path: str) -> str:
        """
        Извлекает аудио из видеофайла.
        
        Args:
            video_path (str): Путь к видеофайлу
            
        Returns:
            str: Путь к извлеченному аудиофайлу
        """
        try:
            # Создаем временный файл для аудио
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                audio_path = tmp_file.name
            
            # Извлекаем аудио асинхронно с помощью ffmpeg
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"Ошибка при извлечении аудио: {stderr.decode()}")
                raise Exception(f"Не удалось извлечь аудио из видео: {stderr.decode()}")
            
            return audio_path
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении аудио из видео: {e}")
            raise
    
    async def _get_transcription(self, audio_path: str) -> str:
        """
        Получает транскрипцию аудиофайла, используя Whisper API.
        
        Args:
            audio_path (str): Путь к аудиофайлу
            
        Returns:
            str: Текст транскрипции
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.audio.transcriptions.create(
                    model="whisper-1",
                    file=open(audio_path, "rb"),
                    language="ru"
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции: {e}")
            raise
    
    def _get_video_duration(self, video_path: str) -> float:
        """
        Получает длительность видеофайла в секундах.
        
        Args:
            video_path (str): Путь к видеофайлу
            
        Returns:
            float: Длительность видео в секундах
        """
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            clip.close()
            return duration
            
        except Exception as e:
            logger.error(f"Ошибка при получении длительности видео: {e}")
            logger.warning("Не удалось определить длительность, возвращаю 0.0")
            return 0.0 