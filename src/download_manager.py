import os
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class DownloadManager:
    """Класс для загрузки и управления файлами"""
    
    def __init__(self, temp_folder="temp"):
        """
        Инициализация менеджера загрузок.
        
        Args:
            temp_folder (str): Папка для временных файлов
        """
        self.temp_folder = temp_folder
        os.makedirs(temp_folder, exist_ok=True)
    
    async def download_file(self, file):
        """
        Скачивает файл из Telegram.
        
        Args:
            file: Объект File из python-telegram-bot
            
        Returns:
            str: Путь к скачанному файлу
        """
        try:
            # Создание пути для сохранения файла
            file_path = os.path.join(self.temp_folder, f"{file.file_unique_id}.mp4")
            
            # Скачивание файла
            await file.download_to_drive(file_path)
            logger.info(f"Файл скачан: {file_path}")
            
            return file_path
        
        except Exception as e:
            logger.error(f"Ошибка при скачивании файла: {e}")
            raise Exception(f"Не удалось скачать файл: {str(e)}")
    
    def cleanup(self, file_path):
        """
        Удаляет временные файлы.
        
        Args:
            file_path (str): Путь к файлу для удаления
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Файл удален: {file_path}")
        except Exception as e:
            logger.warning(f"Не удалось удалить файл {file_path}: {e}")
            
    async def cleanup_temp_folder(self, max_age_hours=24):
        """
        Очищает временную папку от старых файлов.
        
        Args:
            max_age_hours (int): Максимальный возраст файлов в часах
        """
        try:
            # Получаем текущее время
            current_time = asyncio.get_event_loop().time()
            
            # Перебираем все файлы во временной папке
            for filepath in Path(self.temp_folder).glob('*'):
                if filepath.is_file():
                    # Получаем время модификации файла
                    file_modified_time = filepath.stat().st_mtime
                    
                    # Вычисляем возраст файла в часах
                    file_age_hours = (current_time - file_modified_time) / 3600
                    
                    # Если файл старше указанного возраста, удаляем его
                    if file_age_hours > max_age_hours:
                        filepath.unlink()
                        logger.info(f"Удален старый файл: {filepath}")
        
        except Exception as e:
            logger.error(f"Ошибка при очистке временной папки: {e}") 