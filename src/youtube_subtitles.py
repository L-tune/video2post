import logging
import asyncio
import re
import os
import requests
import xml.etree.ElementTree as ET
import json
import subprocess
import time
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

class YouTubeSubtitlesExtractor:
    """Класс для извлечения субтитров из YouTube видео."""
    
    def __init__(self, proxy: str = None, timeout: int = 30):
        """
        Инициализация экстрактора субтитров.
        
        Args:
            proxy (str, optional): Прокси-сервер для запросов к YouTube API (формат: host:port:username:password)
            timeout (int, optional): Таймаут для запросов в секундах
        """
        self.proxy = proxy
        self.timeout = timeout
        self.proxy_dict = self._prepare_proxy_dict() if proxy else None
        
        if proxy:
            logger.info(f"YouTubeSubtitlesExtractor: Инициализирован с прокси (таймаут: {timeout}с)")
        else:
            logger.info(f"YouTubeSubtitlesExtractor: Инициализирован (таймаут: {timeout}с)")

    def _prepare_proxy_dict(self) -> Dict[str, str]:
        """
        Преобразует строку прокси в словарь для использования в запросах.
        
        Returns:
            Dict[str, str]: Словарь с настройками прокси
        """
        try:
            parts = self.proxy.split(':')
            if len(parts) == 4:
                host, port, username, password = parts
                # Для HTTP/HTTPS запросов и yt-dlp используем один и тот же правильный формат
                proxy_url = f"http://{username}:{password}@{host}:{port}"
                
                return {
                    'http': proxy_url,
                    'https': proxy_url,
                    'ytdlp': proxy_url
                }
            elif len(parts) == 2:
                host, port = parts
                proxy_url = f"http://{host}:{port}"
                
                return {
                    'http': proxy_url,
                    'https': proxy_url,
                    'ytdlp': proxy_url
                }
            else:
                logger.warning(f"Неверный формат прокси: {self.proxy}, должен быть host:port или host:port:username:password")
                return None
        except Exception as e:
            logger.error(f"Ошибка при подготовке прокси: {e}")
            return None

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
            # Сначала пробуем с прокси, если он указан
            if self.proxy_dict:
                try:
                    cmd = ["yt-dlp", f"https://www.youtube.com/watch?v={video_id}", 
                           "--dump-json", "--no-playlist", "--skip-download",
                           "--socket-timeout", str(self.timeout),
                           "--retries", "3"]
                    
                    proxy_url = self.proxy_dict.get('ytdlp', self.proxy_dict.get('http'))
                    cmd.extend(["--proxy", proxy_url])
                    logger.info(f"Используем прокси для yt-dlp: {proxy_url}, таймаут: {self.timeout}с")
                    
                    # Запускаем yt-dlp с прокси
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    # Устанавливаем таймаут на выполнение команды
                    try:
                        stdout, stderr = await asyncio.wait_for(
                            proc.communicate(), 
                            timeout=self.timeout
                        )
                        
                        if proc.returncode == 0:
                            # Успешно получили информацию через прокси
                            video_info = json.loads(stdout.decode())
                            logger.info(f"Успешно получена информация о видео через прокси")
                            return video_info
                        else:
                            # Ошибка при получении информации через прокси
                            logger.warning(f"Не удалось получить информацию через прокси: {stderr.decode()}")
                            # Продолжаем выполнение, чтобы попробовать без прокси
                    except asyncio.TimeoutError:
                        logger.warning(f"Таймаут при получении информации через прокси (превышен {self.timeout}с)")
                        # Убиваем процесс, если он еще запущен
                        try:
                            proc.kill()
                        except:
                            pass
                except Exception as e:
                    logger.warning(f"Ошибка при получении информации через прокси: {e}")
            
            # Если прокси не указан или возникла ошибка, пробуем без прокси
            logger.info(f"Пробуем получить информацию о видео без прокси")
            cmd = ["yt-dlp", f"https://www.youtube.com/watch?v={video_id}", 
                  "--dump-json", "--no-playlist", "--skip-download",
                  "--socket-timeout", str(self.timeout),
                  "--retries", "3"]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), 
                    timeout=self.timeout
                )
                
                if proc.returncode != 0:
                    logger.error(f"Ошибка при получении информации о видео без прокси: {stderr.decode()}")
                    return {"title": ""}
                
                # Парсим JSON из вывода yt-dlp
                video_info = json.loads(stdout.decode())
                logger.info(f"Успешно получена информация о видео без прокси")
                return video_info
            except asyncio.TimeoutError:
                logger.error(f"Таймаут при получении информации без прокси (превышен {self.timeout}с)")
                # Убиваем процесс, если он еще запущен
                try:
                    proc.kill()
                except:
                    pass
                return {"title": ""}
            
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
        # Устанавливаем таймаут для сокетов
        import socket
        socket.setdefaulttimeout(self.timeout)
        
        max_attempts = 3
        retry_delay = 2  # секунды между повторными попытками
        
        try:
            # Пробуем сначала с прокси, если он указан
            if self.proxy_dict:
                for attempt in range(max_attempts):
                    try:
                        logger.info(f"Получаем субтитры через прокси: {self.proxy_dict.get('http')} (попытка {attempt+1}/{max_attempts})")
                        proxy_settings = {
                            'http': self.proxy_dict.get('http'),
                            'https': self.proxy_dict.get('https')
                        }
                        
                        transcript_list = YouTubeTranscriptApi.list_transcripts(
                            video_id, 
                            proxies=proxy_settings
                        )
                        logger.info("Получен список транскриптов через прокси")
                        
                        # Сначала пытаемся найти русские субтитры
                        try:
                            transcript = transcript_list.find_transcript(['ru'])
                            logger.info("Найдены русские субтитры через прокси")
                        except NoTranscriptFound:
                            # Если русских нет, берем английские
                            transcript = transcript_list.find_transcript(['en'])
                            logger.info("Найдены английские субтитры через прокси")
                            # Переводим субтитры на русский
                            transcript = transcript.translate('ru')
                            logger.info("Субтитры переведены на русский через прокси")
                        
                        # Получаем текст субтитров
                        transcript_data = transcript.fetch(proxies=proxy_settings)
                        
                        # Объединяем все фрагменты субтитров в один текст
                        transcript_text = " ".join([item['text'] for item in transcript_data])
                        logger.info(f"Успешно получены субтитры через прокси, длина: {len(transcript_text)} символов")
                        return transcript_text
                        
                    except Exception as e:
                        logger.warning(f"Не удалось получить субтитры через прокси (попытка {attempt+1}/{max_attempts}): {e}")
                        if attempt < max_attempts - 1:
                            logger.info(f"Повторная попытка через {retry_delay} секунд...")
                            time.sleep(retry_delay)
                        else:
                            logger.warning(f"Исчерпаны все попытки получения через прокси. Пробуем без прокси.")
            
            # Если прокси не указан или все попытки не удались, пробуем без прокси
            for attempt in range(max_attempts):
                try:
                    logger.info(f"Получаем субтитры без прокси (попытка {attempt+1}/{max_attempts})")
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    logger.info("Получен список транскриптов без прокси")
                    
                    # Сначала пытаемся найти русские субтитры
                    try:
                        transcript = transcript_list.find_transcript(['ru'])
                        logger.info("Найдены русские субтитры")
                    except NoTranscriptFound:
                        # Если русских нет, берем английские
                        transcript = transcript_list.find_transcript(['en'])
                        logger.info("Найдены английские субтитры")
                        # Переводим субтитры на русский
                        transcript = transcript.translate('ru')
                        logger.info("Субтитры переведены на русский")
                    
                    # Получаем текст субтитров
                    transcript_data = transcript.fetch()
                    
                    # Объединяем все фрагменты субтитров в один текст
                    transcript_text = " ".join([item['text'] for item in transcript_data])
                    logger.info(f"Успешно получены субтитры без прокси, длина: {len(transcript_text)} символов")
                    return transcript_text
                    
                except Exception as e:
                    logger.warning(f"Не удалось получить субтитры без прокси (попытка {attempt+1}/{max_attempts}): {e}")
                    if attempt < max_attempts - 1:
                        logger.info(f"Повторная попытка через {retry_delay} секунд...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"Исчерпаны все попытки. Не удалось получить субтитры.")
            
            # Если все попытки не удались
            return ""
            
        except TranscriptsDisabled:
            logger.warning(f"Субтитры отключены для видео {video_id}")
            return ""
        except NoTranscriptFound:
            logger.warning(f"Не найдены субтитры для видео {video_id}")
            return ""
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {e}")
            return "" 