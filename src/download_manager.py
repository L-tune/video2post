import os
import logging
import asyncio
from telegram import File

logger = logging.getLogger(__name__)

class DownloadManager:
    """Класс для управления скачиванием файлов из Telegram."""
    
    def __init__(self, temp_folder="temp"):
        """
        Инициализация менеджера загрузок.
        
        Args:
            temp_folder (str): Путь к папке для временных файлов
        """
        self.temp_folder = temp_folder
        
        # Создание временной папки, если она не существует
        os.makedirs(temp_folder, exist_ok=True)
    
    async def download_file(self, file: File) -> str:
        """
        Скачивает файл из Telegram.
        
        Args:
            file (File): Объект файла из Telegram
            
        Returns:
            str: Путь к скачанному файлу
        """
        try:
            # Генерация уникального имени файла
            file_path_str = file.file_path if file.file_path else f"unknown_{file.file_unique_id}"
            file_ext = os.path.splitext(file_path_str)[1]
            file_name = f"{file.file_unique_id}{file_ext}"
            file_path = os.path.join(self.temp_folder, file_name)
            
            # Скачивание файла
            await file.download_to_drive(custom_path=file_path)
            
            logger.info(f"Файл успешно скачан: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Ошибка при скачивании файла: {e}")
            raise Exception(f"Не удалось скачать файл: {str(e)}")
    
    def cleanup(self, file_path):
        """
        Удаляет временный файл.
        
        Args:
            file_path (str): Путь к файлу для удаления
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Файл удален: {file_path}")
        except Exception as e:
            logger.error(f"Не удалось удалить файл {file_path}: {e}") 