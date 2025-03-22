import logging
import asyncio
import openai

logger = logging.getLogger(__name__)

class ContentGenerator:
    """Класс для генерации текстового контента на основе транскрипции с помощью OpenAI GPT."""
    
    def __init__(self, api_key):
        """
        Инициализация генератора контента.
        
        Args:
            api_key (str): Ключ API OpenAI
        """
        self.api_key = api_key
        openai.api_key = api_key
    
    async def generate_post(self, transcription, style="информативный"):
        """
        Генерирует текстовый пост на основе транскрипции.
        
        Args:
            transcription (str): Текст транскрипции
            style (str): Стиль генерируемого поста
            
        Returns:
            str: Текст поста
        """
        try:
            # Выполнение запроса к GPT в отдельном потоке
            loop = asyncio.get_event_loop()
            post_content = await loop.run_in_executor(
                None, 
                lambda: self._generate_post_sync(transcription, style)
            )
            
            logger.info("Пост успешно сгенерирован")
            return post_content
        
        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {e}")
            raise Exception(f"Не удалось сгенерировать пост: {str(e)}")
    
    def _generate_post_sync(self, transcription, style):
        """
        Синхронный метод для генерации поста.
        
        Args:
            transcription (str): Текст транскрипции
            style (str): Стиль генерируемого поста
            
        Returns:
            str: Текст поста
        """
        # Системный промпт для определения задачи
        system_prompt = f"""
        Ты - профессиональный редактор контента. Твоя задача - преобразовать транскрипцию видео в 
        структурированный {style} пост для Telegram.
        
        Следуй этим правилам:
        1. Сохрани все важные факты и ключевые идеи из оригинала
        2. Разбей текст на логические разделы с подзаголовками
        3. Используй Markdown-разметку для Telegram (жирный текст - **текст**, курсив - *текст*)
        4. Добавь краткое вступление, раскрывающее основную тему
        5. Добавь заключение с основными выводами
        6. Создай привлекательный заголовок с эмодзи
        7. Добавь 3-5 тематических хештегов в конце поста
        8. Оптимальная длина поста - 500-2000 слов в зависимости от сложности темы
        9. Исправь любые грамматические ошибки из оригинальной транскрипции
        
        Готовый пост должен быть самодостаточным и читаться как оригинальный авторский материал, 
        а не как конспект или выжимка из видео.
        """
        
        # Обрезаем транскрипцию, если она слишком длинная
        # GPT-4 имеет ограничение на длину контекста
        max_tokens = 12000  # Примерное ограничение для GPT-4
        if len(transcription) > max_tokens:
            # Обрезаем до примерно 12000 токенов (около 16000 символов)
            transcription = transcription[:16000] + "...[текст транскрипции был обрезан из-за ограничений]"
        
        # Запрос к GPT-4
        response = openai.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Вот транскрипция видео, которую нужно преобразовать в пост:\n\n{transcription}"}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        # Извлечение сгенерированного текста
        return response.choices[0].message.content 