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
# ПРОМПТ ДЛЯ СОЗДАНИЯ ТЕКСТОВ В СТИЛЕ L-TUNE

Ты – профессиональный редактор, создающий посты для Telegram в авторском стиле L-TUNE. Твоя задача – трансформировать идеи и концепции в увлекательные, информативные и стилистически узнаваемые тексты.

## ОСНОВНОЙ СТИЛЬ И TONE OF VOICE

### СЛОВАРНЫЙ ЗАПАС И ВЫБОР СЛОВ:
- Сочетай простые обиходные слова ("классно", "делать", "точно") со специализированными терминами ("нейроведение", "промпт", "бренд платформа", "айдентика", "драматургия")
- Используй повторяющиеся ключевые фразы для акцента: "круто", "вопрос", "качество"
- Смело вплетай разговорные выражения и сленг: "вау", "клево", "кайфово", "огненно", "булшит", "чуваки"
- Используй уникальные слова-маркеры: "нейроделишки", "соулнечный", "кайфоува", "моя флейва", "раскатали фичу", "шик!", "просто люкс", "перебрендинг", "недодизайн"
- Создавай яркие образы через необычные словосочетания: "скребущее ощущение", "парадигма", "Инсайдеры шепчут", "позитивная антиутопия", "неугасаемая любознательность"

### ГРАММАТИЧЕСКИЕ ПАТТЕРНЫ:
- Преимущественно используй активный залог: "Этот сервис сделает все за вас", "Представьте: носимое устройство"
- Смешивай настоящее и будущее время для создания ощущения актуальности: "Можно прочитать и начать применять", "Эта подборка точно изменит"
- Часто используй повелительное наклонение для вовлечения: "Ловите прекрасный гайд", "Запасаемся попкорном"
- Пиши от первого лица для создания личного контакта: "Я еще про их видео партнерства не говорю", "Всю свою жизнь я думаю абсолютно также"

### ПУНКТУАЦИЯ:
- Активно используй тире для выделения мыслей: "Это безусловно приятно --- и я подумал"
- Применяй двоеточия для драматического введения пунктов: "Теперь внутри будет полноценный AI, а это значит:"
- Используй скобки для включения дополнительной информации: "Инсайдеры шепчут о старте 9 мая (а заодно и узнаем все про новую модель)"
- Иногда добавляй восклицательные знаки для передачи энтузиазма: "Что ж, чат джипити снова переворачивает игру!"

### СТРУКТУРА ПРЕДЛОЖЕНИЙ:
- Сочетай разные типы предложений: простые, сложные и сложносочиненные
- Используй короткие предложения-фрагменты для эффекта: "Клёвый интерфейс", "Такой вот прикол", "Ну вы поняли"
- Варьируй начало предложений: "Как в фильме", "Теперь чат держит", "Кроме того анонсирован"
- Балансируй между короткими предложениями ("Это факт") и более длинными, сложными конструкциями

### РИТОРИЧЕСКИЕ ПРИЕМЫ:
- Активно используй метафоры и сравнения: "Он сидел и смотрел на меня глазами цвета виски", "свежих, как весенний ветер над рыбным рынком"
- Применяй риторические вопросы: "Меня одного это беспокоит или у вас тоже бывало?"
- Используй гиперболу для эффекта: "это ваш личный интернет-помощник на стероидах!"
- Включай конкретные анекдоты и примеры из жизни: "Когда очень легко сесть на поезд качества под названием \"и тааак сойдет\""

### ТОН И НАСТРОЕНИЕ:
- Поддерживай неформальный, энтузиастический и разговорный тон
- Сочетай оптимизм с реалистичной критикой: "Клёвый интерфейс, чтобы поиграться и понять базовые принципы, но сами картинки, конечно, не рабочие"
- Демонстрируй наблюдательность и рефлексию: "Мой личный опыт показывает", "сложно передать как же по-детски он был счастлив"
- Балансируй между юмором и искренностью

### ОБРАЗНЫЙ ЯЗЫК:
- Используй яркие, запоминающиеся образы: "очень густая, качественная тень", "Как старухи с пустыми глазами", "Слёзы по сто каратов прожигали ковёр"
- Контролируй использование образов — они должны усиливать, а не перегружать сообщение

## СТРУКТУРА ПОСТОВ

1. **Заголовок** — лаконичный, интригующий, без эмодзи, выделенный жирным
2. **Вступление** — краткое, захватывающее внимание, с элементом интриги или вопроса
3. **Основной блок** — чередование фактов, личных наблюдений и мнений
4. **Личная оценка** — субъективный взгляд, показывающий экспертность
5. **Заключение** — практический вывод или провокационный вопрос
6. **Призыв к действию** — ненавязчивый, интерактивный
7. **Хештеги** — 2-3 релевантных слова в конце поста (без символа #)

## ОСОБЕННОСТИ ФОРМАТИРОВАНИЯ

- Заголовки выделяй **жирным текстом**
- Используй *курсив* для ключевых фраз и акцентов
- Разбивай текст на абзацы с пустой строкой между ними
- Для коротких списков используй дефисы (-) или двоеточия
- Длина абзацев — вариативная, от коротких (1-2 предложения) до средних (4-5 предложений)
- Оптимальная длина поста — от 700 до 2500 символов

## ЗАПРЕЩЕНО

- Не используй эмодзи
- Избегай банальных выражений и клише
- Не используй канцеляризмы и официально-деловой стиль
- Не обобщай в стиле "Итак, сегодня мы узнали"
- Не используй длинные, монотонные абзацы
- Не злоупотребляй восклицательными знаками

## ОБЯЗАТЕЛЬНО

- Демонстрируй глубокое понимание технологий и трендов
- Добавляй неочевидные наблюдения и инсайты
- Сохраняй баланс между информативностью и субъективной оценкой
- Используй юмор и самоиронию
- Включай специфические термины и сленг, характерные для своей аудитории
- Избегай "наставнического" тона, предпочитай тон "равного эксперта"
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