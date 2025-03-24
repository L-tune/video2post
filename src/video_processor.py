import os
import asyncio
import logging
import re
import tempfile
import subprocess
from moviepy.editor import VideoFileClip
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

logger = logging.getLogger(__name__)

# Паттерн для извлечения ID видео из YouTube URL
YOUTUBE_URL_PATTERN = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'

class VideoProcessor:
    """Класс для обработки видеофайлов, YouTube URL и извлечения аудиодорожки."""
    
    def __init__(self, temp_folder, openai_api_key=None, proxy=None):
        """
        Инициализация процессора видео.
        
        Args:
            temp_folder (str): Путь к временной директории для хранения файлов
            openai_api_key (str, optional): API ключ OpenAI для транскрипции
            proxy (str, optional): Прокси-сервер для запросов к YouTube API (формат: http://user:pass@host:port)
        """
        self.temp_folder = temp_folder
        self.openai_api_key = openai_api_key
        self.proxy = proxy
        
        if proxy:
            logger.info(f"Инициализирован VideoProcessor с прокси")
        else:
            logger.info("Инициализирован VideoProcessor без прокси")
    
    async def extract_audio(self, video_path):
        """
        Извлекает аудиодорожку из видеофайла.
        
        Args:
            video_path (str): Путь к видеофайлу
            
        Returns:
            str: Путь к извлеченному аудиофайлу
        """
        try:
            # Получение имени файла без расширения
            base_name = os.path.basename(video_path).split('.')[0]
            audio_path = os.path.join(self.temp_folder, f"{base_name}.mp3")
            
            # Извлечение аудио с использованием moviepy (в отдельном потоке)
            await self._extract_audio_with_moviepy(video_path, audio_path)
            
            logger.info(f"Аудио успешно извлечено из {video_path} в {audio_path}")
            return audio_path
        
        except Exception as e:
            logger.error(f"Ошибка при извлечении аудио: {e}")
            raise Exception(f"Не удалось извлечь аудио из видео: {str(e)}")
    
    async def _extract_audio_with_moviepy(self, video_path, audio_path):
        """
        Извлекает аудио из видео, используя библиотеку moviepy.
        
        Args:
            video_path (str): Путь к видеофайлу
            audio_path (str): Путь для сохранения аудиофайла
        """
        # Запуск CPU-интенсивной задачи в отдельном потоке
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._extract_audio_sync, video_path, audio_path)
    
    def _extract_audio_sync(self, video_path, audio_path):
        """
        Синхронный метод для извлечения аудио.
        
        Args:
            video_path (str): Путь к видеофайлу
            audio_path (str): Путь для сохранения аудиофайла
        """
        with VideoFileClip(video_path) as video:
            # Извлечение аудио и сохранение в MP3 с битрейтом 128 kbps
            video.audio.write_audiofile(
                audio_path,
                bitrate="128k",
                verbose=False,
                logger=None
            )

    async def process_youtube_url(self, youtube_url):
        """
        Обрабатывает YouTube URL, извлекая субтитры или скачивая и транскрибируя аудио.
        
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
            
            # Сначала пробуем получить субтитры через API
            try:
                logger.info(f"Получение субтитров для видео {video_id}")
                result = await self._get_subtitles_via_api(video_id)
                return result
            except Exception as e:
                logger.error(f"Не удалось получить субтитры через API: {e}")
                
                # Если у нас есть прокси, пробуем через него
                if self.proxy:
                    try:
                        logger.info(f"Попытка получения субтитров через прокси")
                        result = await self._get_subtitles_via_proxy(video_id)
                        return result
                    except Exception as proxy_e:
                        logger.error(f"Не удалось получить субтитры через прокси: {proxy_e}")
                
                logger.info("Переключаемся на резервный метод: загрузка видео и транскрипция")
                
                # Если не удалось получить субтитры, используем резервный метод
                if self.openai_api_key:
                    return await self._download_and_transcribe(video_id)
                else:
                    raise Exception("Не удалось получить субтитры, а ключ API для транскрипции не предоставлен")
        
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
            # Сначала пробуем список доступных транскриптов для отладки
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
    
    async def _download_and_transcribe(self, video_id):
        """
        Скачивает видео с YouTube и транскрибирует аудио.
        
        Args:
            video_id (str): ID видео на YouTube
            
        Returns:
            dict: Словарь с информацией о видео и транскрипцией
        """
        try:
            from .transcription import WhisperTranscriber
            
            # Создаем экземпляр WhisperTranscriber
            if not self.openai_api_key:
                raise ValueError("API ключ OpenAI не предоставлен для транскрипции")
            
            transcriber = WhisperTranscriber(self.openai_api_key)
            
            # Формируем пути к временным файлам
            video_path = os.path.join(self.temp_folder, f"{video_id}.mp4")
            audio_path = os.path.join(self.temp_folder, f"{video_id}.mp3")
            
            # Скачиваем видео
            logger.info(f"Загрузка видео {video_id} с YouTube")
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            
            try:
                # Используем yt-dlp для скачивания только аудио
                command = [
                    "yt-dlp", 
                    "-f", "bestaudio", 
                    "-o", audio_path,
                    "--extract-audio",
                    "--audio-format", "mp3",
                    youtube_url
                ]
                
                # Если есть прокси, используем его
                if self.proxy:
                    command.extend(['--proxy', self.proxy])
                
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Ошибка при скачивании аудио: {stderr.decode()}")
                    raise Exception(f"Не удалось скачать аудио: {stderr.decode()}")
                
                logger.info(f"Аудио успешно загружено в {audio_path}")
            except Exception as e:
                logger.error(f"Ошибка при скачивании аудио через yt-dlp: {e}")
                # Альтернативный метод с YoutubeDL
                logger.info("Пробуем альтернативный метод загрузки")
                
                # Пробуем загрузить видео через YoutubeDL
                import urllib.request
                from yt_dlp import YoutubeDL
                
                ydl_opts = {
                    'format': 'bestaudio',
                    'outtmpl': audio_path,
                    'quiet': True
                }
                
                # Добавляем прокси если есть
                if self.proxy:
                    ydl_opts['proxy'] = self.proxy
                
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])
                
                logger.info(f"Аудио успешно загружено в {audio_path}")
            
            # Транскрибируем аудио
            logger.info(f"Транскрибирование аудио {audio_path}")
            transcription = await transcriber.transcribe(audio_path)
            
            # Удаляем временные файлы
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            if os.path.exists(video_path):
                os.remove(video_path)
            
            return {
                'video_id': video_id,
                'transcription': transcription,
                'download_method': 'whisper_transcription'
            }
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке и транскрибировании видео: {e}")
            raise Exception(f"Не удалось скачать и транскрибировать видео: {str(e)}")
    
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