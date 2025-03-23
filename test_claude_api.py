import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Загрузка переменных окружения
load_dotenv()

# Получение ключа API
claude_api_key = os.getenv("CLAUDE_API_KEY")
print(f"Claude API KEY: {claude_api_key[:10]}...")

# Создание клиента Anthropic
client = Anthropic(api_key=claude_api_key)

try:
    # Проверка работы API через простой запрос
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": "Привет! Расскажи кратко, какие у тебя есть возможности?"}
        ]
    )
    print("API Claude работает успешно!")
    print(f"Ответ: {response.content[0].text}")
except Exception as e:
    print(f"Ошибка API Claude: {e}") 