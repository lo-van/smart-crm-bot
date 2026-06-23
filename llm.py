import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def extract_search_params(query: str) -> dict:
    """
    Отправляет запрос в LLM и получает структурированные данные для поиска.
    Возвращает dict с ключами: keywords (список), sphere (строка или None).
    """
    system_prompt = (
        "Ты помощник для умного поиска контактов. Пользователь описывает, кого ищет. "
        "Извлеки из запроса ключевые слова (навыки, технологии, роли) и сферу деятельности. "
        "Верни строго JSON с полями:\n"
        "- keywords: список строк (ключевые слова и синонимы)\n"
        "- sphere: строка или null (общая сфера)\n"
        "Пример: запрос «Нужен дизайнер для лендинга» → "
        '{"keywords": ["дизайнер", "лендинг", "landing", "ui/ux"], "sphere": "дизайн"}'
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        import json
        result = json.loads(response.choices[0].message.content)
        return {
            "keywords": result.get("keywords", []),
            "sphere": result.get("sphere")
        }
    except Exception as e:
        print(f"LLM error: {e}")
        # Возвращаем простой разбор по пробелам, если LLM недоступна
        words = [w.strip().lower() for w in query.split() if len(w.strip()) > 2]
        return {"keywords": words, "sphere": None}
