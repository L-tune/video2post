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
from src.youtube_api import YouTubeAPI

logger = logging.getLogger(__name__)

class YouTubeSubtitlesExtractor:
    """Класс для извлечения субтитров из YouTube видео."""
    
    def __init__(self, api_key: str, timeout: int = 30):
        """
        Инициализация экстрактора субтитров.
        
        Args:
            api_key (str): API ключ от Google Cloud Console
            timeout (int, optional): Таймаут для запросов в секундах
        """
        self.api_key = api_key
        self.timeout = timeout
        self.youtube_api = YouTubeAPI(api_key)
        logger.info(f"YouTubeSubtitlesExtractor: Инициализирован с API ключом (таймаут: {timeout}с)")

    def extract_video_id(self, youtube_url: str) -> str:
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
            video_id = self.extract_video_id(youtube_url)
            if not video_id:
                logger.error(f"Не удалось извлечь ID видео из URL: {youtube_url}")
                raise ValueError(f"Неверная ссылка на YouTube видео: {youtube_url}")
            
            logger.info(f"Получен ID видео: {video_id}")
            
            # Получаем информацию о видео через API
            video_info = self.youtube_api.get_video_info(video_id)
            video_title = video_info.get("title", "")
            
            logger.info(f"Название видео: {video_title}")
            
            # Получаем субтитры через YouTube Transcript API
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru', 'en'])
                transcript_text = " ".join([item['text'] for item in transcript_list])
                logger.info(f"Получены субтитры длиной {len(transcript_text)} символов")
            except Exception as e:
                logger.warning(f"Не удалось получить субтитры через YouTube Transcript API: {e}")
                transcript_text = ""
            
            return {
                "transcript": transcript_text,
                "video_title": video_title,
                "video_id": video_id
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {e}")
            raise Exception(f"Не удалось получить субтитры: {str(e)}")
    
    def _prepare_proxy_dict(self, proxy: str) -> Dict[str, str]:
        """
        Преобразует строку прокси в словарь для использования в запросах.
        
        Args:
            proxy (str): Строка прокси
            
        Returns:
            Dict[str, str]: Словарь с настройками прокси
        """
        try:
            parts = proxy.split(':')
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
                logger.warning(f"Неверный формат прокси: {proxy}, должен быть host:port или host:port:username:password")
                return None
        except Exception as e:
            logger.error(f"Ошибка при подготовке прокси: {e}")
            return None

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
            
            # Если не удалось получить субтитры через YouTube API, пробуем через yt-dlp
            if not transcript:
                logger.info(f"Не удалось получить субтитры через YouTube API, пробуем через yt-dlp")
                transcript = await self._get_transcript_via_ytdlp(video_id)
                if transcript:
                    logger.info(f"Успешно получены субтитры через yt-dlp, длина: {len(transcript)} символов")
            
            return transcript
            
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {e}")
            return ""
            
    async def _get_transcript_via_ytdlp(self, video_id: str) -> str:
        """
        Получает субтитры через yt-dlp как запасной вариант.
        
        Args:
            video_id (str): ID видео
            
        Returns:
            str: Текст субтитров или пустая строка в случае ошибки
        """
        try:
            # Сначала пробуем с прокси, если он указан
            if self.proxy_dict:
                try:
                    proxy_url = self.proxy_dict.get('ytdlp')
                    logger.info(f"Пробуем получить субтитры через yt-dlp с прокси: {proxy_url}")
                    
                    # Команда для получения субтитров через yt-dlp с прокси
                    cmd = [
                        "yt-dlp",
                        f"https://www.youtube.com/watch?v={video_id}",
                        "--write-auto-sub",
                        "--write-sub",
                        "--sub-lang", "ru,en",
                        "--skip-download",
                        "--proxy", proxy_url,
                        "--get-filename", "--output", "%(id)s.%(ext)s"
                    ]
                    
                    # Запускаем yt-dlp с прокси
                    logger.info(f"Выполняем команду yt-dlp: {' '.join(cmd)}")
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await proc.communicate()
                    logger.info(f"yt-dlp вернул код: {proc.returncode}, stdout: {stdout.decode()}, stderr: {stderr.decode()}")
                    
                    if proc.returncode == 0:
                        transcript = self._process_ytdlp_subtitles(video_id)
                        if transcript:
                            return transcript
                except Exception as e:
                    logger.error(f"Ошибка при получении субтитров через yt-dlp с прокси: {type(e).__name__}: {str(e)}")
            
            # Если с прокси не получилось или его нет, пробуем без прокси
            logger.info(f"Пробуем получить субтитры через yt-dlp без прокси")
            cmd = [
                "yt-dlp",
                f"https://www.youtube.com/watch?v={video_id}",
                "--write-auto-sub",
                "--write-sub",
                "--sub-lang", "ru,en",
                "--skip-download",
                "--get-filename", "--output", "%(id)s.%(ext)s"
            ]
            
            logger.info(f"Выполняем команду yt-dlp: {' '.join(cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            logger.info(f"yt-dlp вернул код: {proc.returncode}, stdout: {stdout.decode()}, stderr: {stderr.decode()}")
            
            if proc.returncode == 0:
                transcript = self._process_ytdlp_subtitles(video_id)
                if transcript:
                    return transcript
            
            return ""
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров через yt-dlp: {type(e).__name__}: {str(e)}")
            return ""
            
    def _process_ytdlp_subtitles(self, video_id: str) -> str:
        """
        Обрабатывает субтитры, загруженные через yt-dlp.
        
        Args:
            video_id (str): ID видео
            
        Returns:
            str: Текст субтитров или пустая строка в случае ошибки
        """
        try:
            # Ищем файлы субтитров, загруженные yt-dlp
            subtitle_files = []
            for filename in os.listdir('.'):
                if filename.startswith(video_id) and (filename.endswith('.vtt') or filename.endswith('.srt')):
                    subtitle_files.append(filename)
            
            logger.info(f"Найдено {len(subtitle_files)} файлов субтитров: {subtitle_files}")
            
            if not subtitle_files:
                return ""
            
            # Приоритетные расширения и языки
            priority_lang = ['ru', 'en']
            
            # Сначала ищем русские субтитры, затем английские
            for lang in priority_lang:
                for filename in subtitle_files:
                    if f".{lang}." in filename:
                        logger.info(f"Обрабатываем файл субтитров: {filename}")
                        return self._parse_subtitle_file(filename)
            
            # Если не нашли субтитры с приоритетными языками, берем первый попавшийся
            logger.info(f"Не найдены субтитры на приоритетных языках, используем первый файл: {subtitle_files[0]}")
            return self._parse_subtitle_file(subtitle_files[0])
            
        except Exception as e:
            logger.error(f"Ошибка при обработке файлов субтитров: {type(e).__name__}: {str(e)}")
            return ""
            
    def _parse_subtitle_file(self, filepath: str) -> str:
        """
        Парсит файл субтитров в текст.
        
        Args:
            filepath (str): Путь к файлу субтитров
            
        Returns:
            str: Текст субтитров или пустая строка в случае ошибки
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Удаляем файл после чтения
            try:
                os.remove(filepath)
                logger.info(f"Удален файл субтитров: {filepath}")
            except:
                pass
            
            # Парсинг VTT/SRT файла
            # Удаляем метаданные и временные метки
            lines = []
            for line in content.split('\n'):
                # Пропускаем строки с временными метками, метаданными и пустые строки
                if '-->' in line or line.strip() == '' or line.startswith('WEBVTT') or re.match(r'^\d+$', line.strip()):
                    continue
                lines.append(line.strip())
            
            text = ' '.join(lines)
            return text
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге файла субтитров {filepath}: {type(e).__name__}: {str(e)}")
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
                logger.info(f"Прокси настройки: {self.proxy_dict}")
                for attempt in range(max_attempts):
                    try:
                        proxy_url = self.proxy_dict.get('http', '')
                        logger.info(f"Получаем субтитры через прокси: {proxy_url} (попытка {attempt+1}/{max_attempts})")
                        
                        proxy_settings = {
                            'http': self.proxy_dict.get('http'),
                            'https': self.proxy_dict.get('https')
                        }
                        
                        # Подробная информация о запросе
                        logger.info(f"Детали запроса: video_id={video_id}, proxies={proxy_settings}")
                        
                        try:
                            transcript_list = YouTubeTranscriptApi.list_transcripts(
                                video_id, 
                                proxies=proxy_settings
                            )
                            logger.info("Получен список транскриптов через прокси")
                        except Exception as e:
                            logger.error(f"Ошибка при получении списка транскриптов через прокси: {type(e).__name__}: {str(e)}")
                            raise
                        
                        # Сначала пытаемся найти русские субтитры
                        try:
                            transcript = transcript_list.find_transcript(['ru'])
                            logger.info("Найдены русские субтитры через прокси")
                        except NoTranscriptFound:
                            # Если русских нет, берем английские
                            logger.info("Русские субтитры не найдены, ищем английские")
                            try:
                                transcript = transcript_list.find_transcript(['en'])
                                logger.info("Найдены английские субтитры через прокси")
                                # Переводим субтитры на русский
                                try:
                                    transcript = transcript.translate('ru')
                                    logger.info("Субтитры переведены на русский через прокси")
                                except Exception as e:
                                    logger.error(f"Ошибка при переводе субтитров: {type(e).__name__}: {str(e)}")
                                    raise
                            except NoTranscriptFound as e:
                                logger.error(f"Не найдены ни русские, ни английские субтитры: {str(e)}")
                                raise
                        
                        # Получаем текст субтитров
                        try:
                            transcript_data = transcript.fetch(proxies=proxy_settings)
                            logger.info(f"Получены данные субтитров через прокси: {len(transcript_data)} сегментов")
                        except Exception as e:
                            logger.error(f"Ошибка при получении данных субтитров через прокси: {type(e).__name__}: {str(e)}")
                            raise
                        
                        # Объединяем все фрагменты субтитров в один текст
                        transcript_text = " ".join([item['text'] for item in transcript_data])
                        logger.info(f"Успешно получены субтитры через прокси, длина: {len(transcript_text)} символов")
                        return transcript_text
                        
                    except Exception as e:
                        logger.warning(f"Не удалось получить субтитры через прокси (попытка {attempt+1}/{max_attempts}): {type(e).__name__}: {str(e)}")
                        if attempt < max_attempts - 1:
                            logger.info(f"Повторная попытка через {retry_delay} секунд...")
                            time.sleep(retry_delay)
                        else:
                            logger.warning(f"Исчерпаны все попытки получения через прокси. Пробуем без прокси.")
            
            # Если прокси не указан или все попытки не удались, пробуем без прокси
            logger.info(f"Пробуем получить субтитры без прокси")
            for attempt in range(max_attempts):
                try:
                    logger.info(f"Получаем субтитры без прокси (попытка {attempt+1}/{max_attempts})")
                    
                    try:
                        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                        logger.info("Получен список транскриптов без прокси")
                    except Exception as e:
                        logger.error(f"Ошибка при получении списка транскриптов без прокси: {type(e).__name__}: {str(e)}")
                        raise
                    
                    # Сначала пытаемся найти русские субтитры
                    try:
                        transcript = transcript_list.find_transcript(['ru'])
                        logger.info("Найдены русские субтитры")
                    except NoTranscriptFound:
                        # Если русских нет, берем английские
                        logger.info("Русские субтитры не найдены, ищем английские")
                        try:
                            transcript = transcript_list.find_transcript(['en'])
                            logger.info("Найдены английские субтитры")
                            # Переводим субтитры на русский
                            try:
                                transcript = transcript.translate('ru')
                                logger.info("Субтитры переведены на русский")
                            except Exception as e:
                                logger.error(f"Ошибка при переводе субтитров: {type(e).__name__}: {str(e)}")
                                raise
                        except NoTranscriptFound as e:
                            logger.error(f"Не найдены ни русские, ни английские субтитры: {str(e)}")
                            raise
                    
                    # Получаем текст субтитров
                    try:
                        transcript_data = transcript.fetch()
                        logger.info(f"Получены данные субтитров без прокси: {len(transcript_data)} сегментов")
                    except Exception as e:
                        logger.error(f"Ошибка при получении данных субтитров без прокси: {type(e).__name__}: {str(e)}")
                        raise
                    
                    # Объединяем все фрагменты субтитров в один текст
                    transcript_text = " ".join([item['text'] for item in transcript_data])
                    logger.info(f"Успешно получены субтитры без прокси, длина: {len(transcript_text)} символов")
                    return transcript_text
                    
                except Exception as e:
                    logger.warning(f"Не удалось получить субтитры без прокси (попытка {attempt+1}/{max_attempts}): {type(e).__name__}: {str(e)}")
                    if attempt < max_attempts - 1:
                        logger.info(f"Повторная попытка через {retry_delay} секунд...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"Исчерпаны все попытки. Не удалось получить субтитры: {type(e).__name__}: {str(e)}")
            
            # Если все попытки не удались
            return ""
            
        except TranscriptsDisabled:
            logger.warning(f"Субтитры отключены для видео {video_id}")
            return ""
        except NoTranscriptFound:
            logger.warning(f"Не найдены субтитры для видео {video_id}")
            return ""
        except Exception as e:
            logger.error(f"Ошибка при получении субтитров: {type(e).__name__}: {str(e)}")
            return "" 
