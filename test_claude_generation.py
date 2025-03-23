import os
import sys
import asyncio
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.content_generator import ContentGenerator

async def main():
    # Получаем API ключ из переменных окружения
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    
    if not claude_api_key:
        print("Ошибка: не задан ключ API Claude в .env файле")
        return
    
    print(f"Claude API KEY: {claude_api_key[:10]}...")
    
    # Пример транскрипции для теста
    test_transcription = """
    Привет, друзья! Сегодня я хочу поговорить о том, как искусственный интеллект меняет нашу жизнь.
    
    Искусственный интеллект сейчас находится на пике своего развития. Компании вкладывают миллиарды в разработку
    новых моделей и алгоритмов. Мы видим, как ИИ проникает во все сферы: от медицины до искусства.
    
    Но что это означает для нас? С одной стороны, это новые возможности - автоматизация рутинных задач,
    помощь в сложных вычислениях, создание контента. С другой стороны, возникают вопросы о будущем некоторых профессий.
    
    Я считаю, что ключевой навык будущего - это умение взаимодействовать с ИИ, направлять его работу и использовать
    как инструмент для усиления наших собственных способностей. Не нужно бояться технологий, нужно научиться
    ими пользоваться.
    
    Что вы думаете об этом? Поделитесь в комментариях вашим мнением о том, как ИИ влияет на вашу жизнь или работу.
    """
    
    # Создаем экземпляр генератора контента с реальным ключом Claude API
    generator = ContentGenerator(
        api_key=claude_api_key,  # Передаем тот же ключ в api_key (чтобы не использовать dummy)
        use_claude=True, 
        claude_api_key=claude_api_key
    )
    
    # Генерируем текст с помощью асинхронного метода generate_post
    print("Генерация текста с использованием Claude...")
    generated_text = await generator.generate_post(test_transcription, style="L-TUNE")
    
    print("\nРезультат генерации:\n")
    print(generated_text)
    
    print("\nТест успешно завершен!")

if __name__ == "__main__":
    # Запускаем асинхронную функцию main
    asyncio.run(main()) 