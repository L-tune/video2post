import os
from dotenv import load_dotenv
from openai import OpenAI

# Загрузка переменных окружения
load_dotenv()

# Получение ключа API
api_key = os.getenv("OPENAI_API_KEY")
print(f"API KEY: {api_key[:10]}...")

# Создание клиента OpenAI
client = OpenAI(api_key=api_key)

try:
    # Проверка работы API
    models = client.models.list()
    print("API работает успешно!")
except Exception as e:
    print(f"Ошибка API: {e}")
