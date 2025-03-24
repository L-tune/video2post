import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class YouTubeAPI:
    """Класс для работы с YouTube Data API."""
    
    def __init__(self, api_key: str):
        """
        Инициализация клиента YouTube API.
        
        Args:
            api_key (str): API ключ от Google Cloud Console
        """
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        logger.info("YouTube API клиент инициализирован")

    def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """
        Получает информацию о видео через YouTube Data API.
        
        Args:
            video_id (str): ID видео на YouTube
            
        Returns:
            Dict[str, Any]: Информация о видео
        """
        try:
            request = self.youtube.videos().list(
                part="snippet,contentDetails",
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                logger.warning(f"Видео {video_id} не найдено")
                return {"title": f"Video {video_id}"}
                
            video_data = response['items'][0]
            return {
                "title": video_data['snippet']['title'],
                "description": video_data['snippet']['description'],
                "published_at": video_data['snippet']['publishedAt'],
                "channel_title": video_data['snippet']['channelTitle']
            }
            
        except HttpError as e:
            logger.error(f"Ошибка YouTube API при получении информации о видео: {e}")
            return {"title": f"Video {video_id}"}
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении информации о видео: {e}")
            return {"title": f"Video {video_id}"} 