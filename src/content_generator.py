import logging
import asyncio
import openai
import anthropic

logger = logging.getLogger(__name__)

class ContentGenerator:
    """Класс для генерации текстового контента на основе транскрипции с помощью OpenAI GPT или Claude."""
    
    def __init__(self, api_key, claude_api_key=None):
        """
        Инициализация генератора контента.
        
        Args:
            api_key (str): Ключ API OpenAI
            claude_api_key (str, optional): Ключ API Claude
        """
        self.api_key = api_key
        openai.api_key = api_key
        
        self.claude_api_key = claude_api_key
        self.claude_client = None
        if claude_api_key:
            self.claude_client = anthropic.Anthropic(api_key=claude_api_key)
    
    async def generate_post(self, transcription, style="информативный", use_claude=True):
        """
        Генерирует текстовый пост на основе транскрипции.
        
        Args:
            transcription (str): Текст транскрипции
            style (str): Стиль генерируемого поста
            use_claude (bool): Использовать Claude вместо GPT-4
            
        Returns:
            str: Текст поста
        """
        try:
            # Выполнение запроса к AI в отдельном потоке
            loop = asyncio.get_event_loop()
            post_content = await loop.run_in_executor(
                None, 
                lambda: self._generate_post_sync(transcription, style, use_claude)
            )
            
            logger.info("Пост успешно сгенерирован")
            return post_content
        
        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {e}")
            raise Exception(f"Не удалось сгенерировать пост: {str(e)}")
    
    def _generate_post_sync(self, transcription, style, use_claude=True):
        """
        Синхронный метод для генерации поста.
        
        Args:
            transcription (str): Текст транскрипции
            style (str): Стиль генерируемого поста
            use_claude (bool): Использовать Claude вместо GPT-4
            
        Returns:
            str: Текст поста
        """
        # Системный промпт для определения задачи
        system_prompt = f"""
        Ты – профессиональный редактор, создающий посты в стиле популярного блогера-технологического эксперта. Твоя задача – преобразовать транскрипцию видео в увлекательный пост для Telegram в авторском стиле.

        СТИЛЬ И VOICE:
        - Неформальный и разговорный тон
        - Мнение от первого лица ("я думаю", "я заметил")
        - Умный, но доступный – объясняешь сложные технические концепты просто
        - БЕЗ ЭМОДЗИ - не используй их вообще
        - Иногда добавляешь тонкий юмор или самоиронию
        - Демонстрируешь глубокое понимание технологий и маркетинга

        СТРУКТУРА:
        1. Заголовок без эмодзи (например: "Новая магия от Google")
        2. Ключевые идеи в простой, структурированной форме
        3. Личное мнение и наблюдения
        4. Практические выводы или рекомендации
        5. В конце часто добавляй призыв к действию или интерактивный элемент (например: "накидайте огоньков если интересно")
        6. Добавь 2-3 релевантных хештега в конце без символов # (просто слова через пробел)

        ФОРМАТ ДЛЯ TELEGRAM:
        - Заголовки выделяй **жирным текстом**
        - Текст разбивай на абзацы для легкого восприятия
        - Используй *курсив* для выделения важных фраз
        - Для списков используй дефисы (-) или звездочки (*)
        - Для кода и технических терминов используй `код`
        - Оптимальная длина - от 500 до 2000 символов
        - Между абзацами оставляй пустую строку

        ЗАПРЕЩЕНО:
        - Не используй эмодзи совсем
        - Не используй банальные фразы и клише
        - Не делай много абзацев с 1-2 короткими предложениями
        - Избегай формального тона и академического стиля
        - Не подводи итоги в формате "Вот что мы узнали сегодня"
        - Не используй сложное форматирование, недоступное в Telegram

        ОБЯЗАТЕЛЬНО:
        - Сохрани основные идеи и смысл оригинальной транскрипции
        - Добавь личное мнение об обсуждаемой технологии/теме
        - Передай экспертность и глубину понимания темы
        - Выдели 1-2 неочевидных наблюдения или инсайта
        - Используй только поддерживаемое в Telegram форматирование: **жирный**, *курсив*, `код`, ~~зачеркнутый~~

        ДОПОЛНИТЕЛЬНО - ПРОМПТЫ ДЛЯ ИЗОБРАЖЕНИЙ:
        - В конце сообщения, если тема подходит для иллюстрации, добавь блок "ПРОМПТ ДЛЯ ИЗОБРАЖЕНИЯ"
        - Внутри этого блока создай 1-2 промпта на английском языке
        - Каждый промпт должен начинаться со слова "LTUNE"
        - Всегда описывай LTUNE как лысого (или с очень короткими волосами) мужчину около 30 лет с серьгой
        - Интегрируй это описание в сценарий, связанный с темой поста
        - Добавляй детали окружения, освещения, выражения лица и позы
        - Используй богатый, образный язык
        - Избегай технических терминов, специфичных для систем генерации изображений
        - Не упоминай цвет глаз LTUNE

        Пример блока с промптом:
        
        ПРОМПТ ДЛЯ ИЗОБРАЖЕНИЯ:
        ```
        LTUNE, a bald man in his early 30s with an earring, sits in front of multiple monitors displaying complex code, his face illuminated by the screens' glow. His fingers dance across a mechanical keyboard as he concentrates intensely on solving a challenging programming problem. The office around him is modern and minimalist, with soft ambient lighting creating a focused atmosphere.
        ```

        Готовый пост должен выглядеть как оригинальный авторский материал человека, который глубоко разбирается в технологиях и любит делиться своими наблюдениями.
        """
        
        # Обрезаем транскрипцию, если она слишком длинная
        # AI имеет ограничение на длину контекста
        max_tokens = 12000
        if len(transcription) > max_tokens:
            # Обрезаем до примерно 12000 токенов (около 16000 символов)
            transcription = transcription[:16000] + "...[текст транскрипции был обрезан из-за ограничений]"
        
        if use_claude and self.claude_client:
            # Используем Claude API
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=4000,
                temperature=0.8,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Вот транскрипция видео, которую нужно преобразовать в пост в указанном стиле:\n\n{transcription}"}
                ]
            )
            # Извлечение сгенерированного текста
            return response.content[0].text
        else:
            # Запрос к GPT-4
            response = openai.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Вот транскрипция видео, которую нужно преобразовать в пост в указанном стиле:\n\n{transcription}"}
                ],
                temperature=0.8,
                max_tokens=4000
            )
            
            # Извлечение сгенерированного текста
            return response.choices[0].message.content 