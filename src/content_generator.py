import logging
import asyncio
import os
from openai import OpenAI
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class ContentGenerator:
    """Класс для генерации текстового контента на основе транскрипции с помощью AI моделей."""
    
    def __init__(self, api_key, use_claude=True, claude_api_key=None):
        """
        Инициализация генератора контента.
        
        Args:
            api_key (str): Ключ API OpenAI
            use_claude (bool): Использовать Claude вместо OpenAI
            claude_api_key (str): Ключ API Claude
        """
        self.use_claude = use_claude
        
        if use_claude:
            if not claude_api_key:
                error_msg = "ContentGenerator: Не предоставлен API ключ Claude"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.info(f"ContentGenerator: Получен ключ API Claude: {claude_api_key[:10]}...")
            self.api_key = claude_api_key
            
            # Создание клиента Claude
            try:
                self.client = Anthropic(api_key=claude_api_key)
                logger.info("ContentGenerator: Клиент Claude успешно создан")
            except Exception as e:
                logger.error(f"ContentGenerator: Ошибка при создании клиента Claude: {e}")
                raise
        else:
            logger.info(f"ContentGenerator: Получен ключ API OpenAI: {api_key[:10]}...")
            
            # Проверка на пустой или неверный ключ
            if not api_key or api_key == "OPENAI_API_KEY" or not isinstance(api_key, str):
                error_msg = f"ContentGenerator: Некорректный ключ API: {type(api_key)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            self.api_key = api_key
            
            # Создание клиента OpenAI с явным указанием ключа API
            try:
                self.client = OpenAI(api_key=api_key)
                logger.info("ContentGenerator: Клиент OpenAI успешно создан")
            except Exception as e:
                logger.error(f"ContentGenerator: Ошибка при создании клиента OpenAI: {e}")
                raise
    
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
            # Выполнение запроса к модели в отдельном потоке
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
        try:
            logger.info(f"Начинаю генерацию поста в стиле: {style}")
            logger.info(f"Использую API ключ: {self.api_key[:10]}...")
            
            # Системный промпт для определения задачи
            system_prompt = """# ПРОМПТ ДЛЯ СОЗДАНИЯ ТЕКСТОВ В СТИЛЕ L-TUNE

Ты – редактор, создающий короткие, содержательные тексты в авторском стиле L-TUNE. Трансформируй идеи в тексты с особой стилистикой для Telegram.

## ОСНОВНОЙ СТИЛЬ И TONE OF VOICE

- Пиши экспертно и глубоко, но без излишней формальности
- Избегай риторических вопросов полностью
- Сочетай технические термины с оригинальными авторскими метафорами
- Не используй банальные выражения и очевидные мысли
- Вставляй необычные неологизмы и языковые находки, но не более 1-2 на весь текст

## ОСОБЕННОСТИ ОФОРМЛЕНИЯ:

- Используй «—» тире для выделения мыслей и создания смысловых пауз
  Пример: "Элегантное решение в духе классического маркетинга Apple --- присвоить себе аббревиатуру AI через название Apple Intelligence"

- Формируй 1-2 сложных предложения с несколькими придаточными и вводными конструкциями
  Пример: "Истинная первопричина, по которой девушка хочет купить очень красивую шубу, связана не столько с желанием самой шубы, сколько с глубинным стремлением к социальному признанию"

- Создавай неожиданные образы и сравнения
  Пример: "Все вместе рождало сложное ощущение жары, нищеты, смрада и оптимизма"

- Включай 1-2 экспертных наблюдения, показывающих глубокое понимание темы
  Пример: "Мой личный опыт показывает, что кроме обещанной оптимизации и упрощения жизни AI может принести стресс, когнитивный диссонанс и информационную перегрузку"

## СТРУКТУРА:

1. **Заголовок** — лаконичный, без вопросов, выделенный жирным
2. **Текст** — 2-3 абзаца общим объемом 400-600 символов
   - Первый абзац: введение в тему с необычного ракурса
   - Средние абзацы: экспертная оценка с техническими деталями
   - Финальный абзац: личное наблюдение или неожиданный вывод

## ЗАПРЕЩЕНО:

- Не используй риторические вопросы
- Не используй эмодзи
- Не используй хештеги в конце текста
- Не пиши коротких, отрывистых предложений подряд
- Не используй фразы: "ребята", "черт возьми", "знаете что?", "представьте себе", "и знаете что?"
- Не пиши больше 4 абзацев
- Не используй восклицательные знаки больше 1 раза за весь текст

## ОБЯЗАТЕЛЬНО:

- Пиши от первого лица
- Добавляй технические детали и нюансы
- Используй активный залог
- Включай 1-2 свежие метафоры
- Создавай ощущение экспертности через контент, а не через прямые заявления
- Пиши ТОЛЬКО на русском языке"""
            
            # Обрезаем транскрипцию, если она слишком длинная
            max_tokens = 12000  # Примерное ограничение для моделей
            if len(transcription) > max_tokens:
                # Обрезаем до примерно 12000 токенов (около 16000 символов)
                transcription = transcription[:16000] + "...[текст транскрипции был обрезан из-за ограничений]"
            
            if self.use_claude:
                # Запрос к Claude
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20240620",  # Используем актуальную версию Claude 3.5 Sonnet
                    max_tokens=1000,
                    system=system_prompt,  # Передаем системный промпт отдельно
                    messages=[
                        {"role": "user", "content": f"Вот транскрипция видео, которую нужно преобразовать в пост в стиле L-TUNE:\n\n{transcription}"}
                    ]
                )
                # Извлечение сгенерированного текста
                return response.content[0].text
            else:
                # Запрос к GPT-4
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Вот транскрипция видео, которую нужно преобразовать в пост в стиле L-TUNE:\n\n{transcription}"}
                    ],
                    temperature=0.8,
                    max_tokens=2000
                )
                # Извлечение сгенерированного текста
                return response.choices[0].message.content 
        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {e}")
            raise Exception(f"Не удалось сгенерировать пост: {str(e)}")