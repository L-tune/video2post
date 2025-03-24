import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def test_youtube_api():
    # Получаем API ключ
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("Ошибка: Не установлена переменная окружения YOUTUBE_API_KEY")
        return

    try:
        # Создаем клиент YouTube API
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Тестовый запрос для получения информации о видео
        video_id = 'dQw4w9WgXcQ'  # Rick Astley - Never Gonna Give You Up
        request = youtube.videos().list(
            part="snippet",
            id=video_id
        )
        
        # Выполняем запрос
        response = request.execute()
        
        if response['items']:
            video_data = response['items'][0]['snippet']
            print("\nУспешно получена информация о видео:")
            print(f"Название: {video_data['title']}")
            print(f"Канал: {video_data['channelTitle']}")
            print(f"Описание: {video_data['description'][:200]}...")
        else:
            print("Видео не найдено")
            
    except HttpError as e:
        print(f"Ошибка YouTube API: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")

if __name__ == "__main__":
    test_youtube_api() 