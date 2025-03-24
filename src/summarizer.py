import logging
import asyncio
import re
from typing import List, Dict, Any
from openai import OpenAI

logger = logging.getLogger(__name__)

class VideoSummarizer:
    """Класс для эффективной саммаризации транскрипций видео с использованием Map-Reduce подхода."""
    
    def __init__(self, api_key):
        """
        Инициализация саммаризатора.
        
        Args:
            api_key (str): Ключ API OpenAI
        """
        self.api_key = api_key
        
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("VideoSummarizer: Клиент OpenAI успешно создан")
        except Exception as e:
            logger.error(f"VideoSummarizer: Ошибка при создании клиента OpenAI: {e}")
            raise
    
    async def summarize(self, transcript: str) -> str:
        """
        Саммаризирует транскрипцию видео с использованием Map-Reduce подхода.
        
        Args:
            transcript (str): Полный текст транскрипции
            
        Returns:
            str: Саммаризированный текст
        """
        try:
            # Оценка длины текста в токенах (приблизительно)
            estimated_tokens = len(transcript.split()) * 1.3  # Примерное соотношение слов к токенам
            
            logger.info(f"Начинаю саммаризацию текста длиной ~{int(estimated_tokens)} токенов")
            
            # Если текст короткий, не нужно разбивать
            if estimated_tokens < 8000:
                return await self._direct_summarize(transcript)
            
            # Если текст длинный, используем Map-Reduce
            chunks = self._split_into_chunks(transcript)
            logger.info(f"Текст разбит на {len(chunks)} частей")
            
            # Map: Саммаризация каждого чанка отдельно (параллельно)
            chunk_summaries = await self._map_summarize_chunks(chunks)
            logger.info(f"Выполнена саммаризация {len(chunk_summaries)} частей")
            
            # Reduce: Объединение саммари в финальное саммари
            return await self._reduce_summaries(chunk_summaries)
        
        except Exception as e:
            logger.error(f"Ошибка при саммаризации: {e}")
            raise Exception(f"Не удалось саммаризировать транскрипцию: {str(e)}")
    
    def _split_into_chunks(self, text: str, max_tokens: int = 3000, overlap: int = 200) -> List[str]:
        """
        Разбивает текст на перекрывающиеся чанки.
        
        Args:
            text (str): Текст для разбиения
            max_tokens (int): Максимальное количество токенов в одном чанке
            overlap (int): Количество токенов для перекрытия
            
        Returns:
            List[str]: Список чанков
        """
        # Делим текст на предложения для лучшей сегментации
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            # Оцениваем размер предложения в токенах
            sentence_size = len(sentence.split()) * 1.3
            
            # Если текущий чанк + новое предложение больше максимального размера
            if current_size + sentence_size > max_tokens and current_chunk:
                # Сохраняем текущий чанк
                chunks.append(" ".join(current_chunk))
                
                # Берем последние предложения для перекрытия
                overlap_tokens = 0
                overlap_chunk = []
                for s in reversed(current_chunk):
                    s_size = len(s.split()) * 1.3
                    if overlap_tokens + s_size <= overlap:
                        overlap_chunk.insert(0, s)
                        overlap_tokens += s_size
                    else:
                        break
                
                # Начинаем новый чанк с перекрывающимися предложениями
                current_chunk = overlap_chunk.copy()
                current_size = overlap_tokens
            
            # Добавляем предложение к текущему чанку
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Добавляем последний чанк
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    async def _map_summarize_chunks(self, chunks: List[str]) -> List[str]:
        """
        Суммаризирует каждый чанк отдельно.
        
        Args:
            chunks (List[str]): Список чанков для суммаризации
            
        Returns:
            List[str]: Список суммаризированных чанков
        """
        # Создаем асинхронные задачи для каждого чанка
        tasks = []
        for i, chunk in enumerate(chunks):
            task = asyncio.create_task(self._summarize_chunk(chunk, i))
            tasks.append(task)
        
        # Ждем выполнения всех задач
        summaries = await asyncio.gather(*tasks)
        return summaries
    
    async def _summarize_chunk(self, chunk: str, chunk_index: int) -> str:
        """
        Суммаризирует один чанк.
        
        Args:
            chunk (str): Текст чанка
            chunk_index (int): Индекс чанка (для логирования)
            
        Returns:
            str: Суммаризированный текст
        """
        logger.info(f"Начинаю суммаризацию чанка {chunk_index+1}")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._summarize_chunk_sync(chunk, chunk_index)
        )
        
        logger.info(f"Завершена суммаризация чанка {chunk_index+1}")
        return result
    
    def _summarize_chunk_sync(self, chunk: str, chunk_index: int) -> str:
        """
        Синхронная версия суммаризации чанка с использованием GPT-4o mini.
        
        Args:
            chunk (str): Текст чанка
            chunk_index (int): Индекс чанка (для логирования)
            
        Returns:
            str: Суммаризированный текст
        """
        try:
            # Используем более экономичную модель GPT-4o-mini
            system_prompt = """Ты специалист по извлечению ключевой информации из текста.
Твоя задача - извлечь и структурировать ключевые факты и идеи из предоставленного фрагмента текста.

Пожалуйста, следуй этим рекомендациям:
1. Выдели 3-5 ключевых фактов или идей
2. Сохрани важные числа, имена и технические детали
3. Удали повторения и несущественную информацию
4. Представь результат в виде кратких, но содержательных абзацев
5. Пиши только на русском языке"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Вот фрагмент транскрипции видео, который нужно проанализировать и извлечь ключевую информацию:\n\n{chunk}"}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Ошибка при суммаризации чанка {chunk_index+1}: {e}")
            raise
    
    async def _reduce_summaries(self, summaries: List[str]) -> str:
        """
        Объединяет саммари чанков в финальное саммари.
        
        Args:
            summaries (List[str]): Список саммари чанков
            
        Returns:
            str: Финальное саммари
        """
        logger.info("Начинаю объединение саммари чанков")
        
        # Объединяем все саммари в один текст
        combined_summary = "\n\n".join([f"--- Часть {i+1} ---\n{summary}" for i, summary in enumerate(summaries)])
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._reduce_summaries_sync(combined_summary)
        )
        
        logger.info("Завершено объединение саммари")
        return result
    
    def _reduce_summaries_sync(self, combined_summary: str) -> str:
        """
        Синхронная версия объединения саммари.
        
        Args:
            combined_summary (str): Объединенные саммари чанков
            
        Returns:
            str: Финальное саммари
        """
        try:
            system_prompt = """Ты специалист по созданию структурированных саммари.
Тебе предоставлены отдельные саммари частей видео, и твоя задача объединить их в цельное, связное саммари.

Пожалуйста, следуй этим рекомендациям:
1. Создай единое, логически связное саммари, объединяющее всю ключевую информацию
2. Удали повторения и перекрытия, неизбежные из-за разбиения на части
3. Структурируй информацию в логическом порядке, группируя связанные идеи
4. Разбей результат на секции с подзаголовками
5. В конце добавь раздел "ОСНОВНЫЕ ВЫВОДЫ" с 2-3 ключевыми мыслями

КЛЮЧЕВЫЕ ФАКТЫ:
• [Список ключевых фактов в формате маркированного списка]

ОСНОВНЫЕ ВЫВОДЫ:
[1-2 предложения с главными выводами из видео]

Пиши только на русском языке."""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Используем более мощную модель для финального саммари
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Вот саммари отдельных частей видео, которые нужно объединить в финальное саммари:\n\n{combined_summary}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Ошибка при объединении саммари: {e}")
            raise
    
    async def _direct_summarize(self, text: str) -> str:
        """
        Прямая саммаризация текста без разбиения на чанки.
        
        Args:
            text (str): Текст для саммаризации
            
        Returns:
            str: Саммаризированный текст
        """
        logger.info("Начинаю прямую саммаризацию текста")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._direct_summarize_sync(text)
        )
        
        logger.info("Завершена прямая саммаризация")
        return result
    
    def _direct_summarize_sync(self, text: str) -> str:
        """
        Синхронная версия прямой саммаризации.
        
        Args:
            text (str): Текст для саммаризации
            
        Returns:
            str: Саммаризированный текст
        """
        try:
            system_prompt = """Ты специалист по анализу видео и созданию структурированных саммари.
Твоя задача - создать информативное и хорошо структурированное саммари видео на основе его транскрипции.

Пожалуйста, следуй этим рекомендациям:
1. Выдели 5-7 ключевых фактов или идей из видео
2. Структурируй информацию в логическом порядке, группируя связанные идеи
3. Разбей результат на секции с подзаголовками, если это уместно
4. Представь ключевые факты в формате маркированного списка
5. В конце добавь раздел "ОСНОВНЫЕ ВЫВОДЫ" с 2-3 ключевыми мыслями

КЛЮЧЕВЫЕ ФАКТЫ:
• [Список ключевых фактов в формате маркированного списка]

ОСНОВНЫЕ ВЫВОДЫ:
[1-2 предложения с главными выводами из видео]

Пиши только на русском языке."""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Вот транскрипция видео, на основе которой нужно создать саммари:\n\n{text}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Ошибка при прямой саммаризации: {e}")
            raise 