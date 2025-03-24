import os
import sys
import asyncio
import logging
import dotenv
import tempfile
import argparse
import time
from src.video_processor import VideoProcessor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("test.log")
    ]
)

logger = logging.getLogger(__name__)

# Загрузка переменных окружения
dotenv.load_dotenv()

# Прокси по умолчанию для Render
DEFAULT_PROXY = "194.226.4.30:63825:MkBea3Vy:P6S5C8zd"

async def test_youtube_transcript(youtube_url, proxy=None, timeout=30):
    """
    Тестирование получения транскрипции из YouTube видео.
    
    Args:
        youtube_url (str): URL YouTube видео для тестирования
        proxy (str, optional): Прокси для YouTube API
        timeout (int, optional): Таймаут для запросов в секундах
    """
    logger.info(f"Начинаю тестирование получения транскрипции для URL: {youtube_url}")
    
    start_time = time.time()
    
    try:
        # Инициализация видео процессора
        processor = VideoProcessor(proxy=proxy, timeout=timeout)
        
        # Получение данных из YouTube
        result = await processor.process_youtube_url(youtube_url)
        
        # Расчет затраченного времени
        elapsed_time = time.time() - start_time
        
        # Вывод результатов
        print("\n" + "="*50)
        print(f"🎬 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ДЛЯ: {youtube_url}")
        print("="*50)
        
        # Вывод информации о видео
        print(f"\n📌 Название видео: {result.get('video_title', 'Н/Д')}")
        print(f"📌 ID видео: {result.get('video_id', 'Н/Д')}")
        
        # Вывод части транскрипции (первые 500 символов)
        transcript = result.get('transcript', '')
        print("\n📄 ТРАНСКРИПЦИЯ (первые 500 символов):")
        print("-"*50)
        print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
        print("-"*50)
        
        # Статистика
        transcript_len = len(transcript)
        
        print(f"\n📊 СТАТИСТИКА:")
        print(f"- Длина транскрипции: {transcript_len} символов")
        print(f"- Время выполнения: {elapsed_time:.2f} секунд")
        
        logger.info(f"Тестирование завершено успешно за {elapsed_time:.2f} секунд")
        return True
        
    except Exception as e:
        # Расчет затраченного времени
        elapsed_time = time.time() - start_time
        
        logger.error(f"Ошибка при тестировании: {e} (за {elapsed_time:.2f} секунд)")
        print(f"\n❌ ОШИБКА ТЕСТИРОВАНИЯ: {e}")
        print(f"- Время выполнения до ошибки: {elapsed_time:.2f} секунд")
        return False

async def test_proxy_settings(youtube_url, proxy, timeout=30):
    """
    Тестирует настройки прокси с разными параметрами.
    
    Args:
        youtube_url (str): URL YouTube видео для тестирования
        proxy (str): Прокси для тестирования
        timeout (int): Таймаут для запросов в секундах
    """
    print("\n" + "="*80)
    print(f"🔍 ТЕСТИРОВАНИЕ ПРОКСИ: {proxy or 'Без прокси'} (таймаут: {timeout}с)")
    print("="*80)
    
    success = await test_youtube_transcript(youtube_url, proxy, timeout)
    
    if success:
        print("\n✅ Тест с прокси пройден успешно!")
    else:
        print("\n❌ Тест с прокси завершился с ошибкой.")
    
    return success

async def main():
    # Настройка аргументов командной строки
    parser = argparse.ArgumentParser(description='Тестирование получения транскрипции видео')
    parser.add_argument('--youtube', help='URL YouTube видео для тестирования')
    parser.add_argument('--proxy', help='Прокси-сервер для доступа к YouTube API (host:port:username:password)')
    parser.add_argument('--no-proxy', action='store_true', help='Не использовать прокси (даже по умолчанию)')
    parser.add_argument('--timeout', type=int, default=30, help='Таймаут для запросов в секундах')
    parser.add_argument('--test-all', action='store_true', help='Протестировать все варианты (с прокси и без)')
    args = parser.parse_args()
    
    # Тестовый URL по умолчанию
    youtube_url = args.youtube or "https://www.youtube.com/watch?v=UQYV8--TZqI"
    timeout = args.timeout
    
    if args.test_all:
        # Тестируем все варианты
        print("\n🧪 ЗАПУСК ПОЛНОГО ТЕСТИРОВАНИЯ (с прокси и без)")
        
        # Тест без прокси
        success_no_proxy = await test_proxy_settings(youtube_url, None, timeout)
        
        # Тест с прокси по умолчанию
        success_with_proxy = await test_proxy_settings(youtube_url, DEFAULT_PROXY, timeout)
        
        # Тест с указанным прокси (если есть)
        success_custom_proxy = True
        if args.proxy and args.proxy != DEFAULT_PROXY:
            success_custom_proxy = await test_proxy_settings(youtube_url, args.proxy, timeout)
        
        # Вывод общих результатов
        print("\n" + "="*80)
        print("📋 ИТОГИ ТЕСТИРОВАНИЯ:")
        print(f"✓ Без прокси: {'Успешно ✅' if success_no_proxy else 'Ошибка ❌'}")
        print(f"✓ С прокси по умолчанию: {'Успешно ✅' if success_with_proxy else 'Ошибка ❌'}")
        if args.proxy and args.proxy != DEFAULT_PROXY:
            print(f"✓ С указанным прокси: {'Успешно ✅' if success_custom_proxy else 'Ошибка ❌'}")
        print("="*80)
        
        # Возвращаем успех, если хотя бы один тест прошел успешно
        if success_no_proxy or success_with_proxy or (args.proxy and success_custom_proxy):
            print("\n✅ Как минимум один метод работает успешно!")
            return True
        else:
            print("\n❌ Все методы завершились с ошибкой.")
            sys.exit(1)
    else:
        # Определяем, какой прокси использовать
        proxy = None
        if not args.no_proxy:
            proxy = args.proxy or DEFAULT_PROXY
        
        # Выводим информацию о параметрах
        print(f"Таймаут: {timeout} секунд")
        if proxy:
            print(f"Используем прокси: {proxy}")
        else:
            print("Тестирование без прокси")
        
        # Тестируем YouTube URL
        success = await test_youtube_transcript(youtube_url, proxy, timeout)
        
        if success:
            print("\n✅ Тест пройден успешно!")
        else:
            print("\n❌ Тест завершился с ошибкой.")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 