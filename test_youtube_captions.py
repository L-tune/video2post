import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def test_youtube_captions():
    # Получаем API ключ
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("Ошибка: Не установлена переменная окружения YOUTUBE_API_KEY")
        return

    try:
        # Создаем клиент YouTube API
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # ID видео для теста
        video_id = 'dQw4w9WgXcQ'
        
        # Получаем список доступных субтитров
        request = youtube.captions().list(
            part="snippet",
            videoId=video_id
        )
        
        # Выполняем запрос
        response = request.execute()
        
        if response.get('items'):
            print("\nДоступные субтитры:")
            for item in response['items']:
                print(f"- {item['snippet']['language']}: {item['snippet']['name']}")
                
            # Получаем ID первого доступного субтитра
            caption_id = response['items'][0]['id']
            
            # Получаем сам текст субтитра
            request = youtube.captions().download(
                id=caption_id
            )
            response = request.execute()
            
            if response:
                print("\nПервые 200 символов субтитров:")
                print(response.decode('utf-8')[:200])
            else:
                print("\nНе удалось получить текст субтитров")
        else:
            print("\nСубтитры не найдены для этого видео")
            
    except HttpError as e:
        print(f"Ошибка YouTube API: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")

if __name__ == "__main__":
    test_youtube_captions() 