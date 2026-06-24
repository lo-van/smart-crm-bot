# Модуль llm.py – заглушка без зависимостей.
# Позже сюда можно будет подключить любую LLM.
import os

async def extract_search_params(query: str) -> dict:
    """
    Простой разбор запроса – разбивает на слова.
    При подключении LLM замените эту функцию.
    """
    words = [w.strip().lower() for w in query.split() if len(w.strip()) > 2]
    return {"keywords": words, "sphere": None}
