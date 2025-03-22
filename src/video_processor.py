import os
import asyncio
import logging
from moviepy.editor import VideoFileClip

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Класс для обработки видеофайлов и извлечения аудиодорожки."""
    
    def __init__(self, temp_folder):
        """
        Инициализация процессора видео.
        
        Args:
            temp_folder (str): Путь к временной директории для хранения файлов
        """
        self.temp_folder = temp_folder
    
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