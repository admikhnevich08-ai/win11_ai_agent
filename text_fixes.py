# -*- coding: utf-8 -*-
"""
Постобработка: заменяем английские слова на русские.
"""
import re


# Словарь замен (регистрозависимые и нет)
REPLACEMENTS = [
    # Технические термины
    ("neural networks", "нейронные сети"),
    ("neural network", "нейронная сеть"),
    ("machine learning", "машинное обучение"),
    ("deep learning", "глубокое обучение"),
    ("natural language processing", "обработка естественного языка"),
    ("NLP", "обработка языка"),
    ("large language model", "большая языковая модель"),
    ("large language models", "большие языковые модели"),
    ("LLM", "языковая модель"),
    ("LLMs", "языковые модели"),
    ("AI", "ИИ"),
    ("artificial intelligence", "искусственный интеллект"),
    ("deep neural networks", "глубокие нейронные сети"),
    ("transformer", "трансформер"),
    ("transformers", "трансформеры"),
    ("dataset", "набор данных"),
    ("datasets", "наборы данных"),
    ("tokenization", "токенизация"),
    ("fine-tuning", "дообучение"),
    ("fine tuning", "дообучение"),
    ("pre-training", "предобучение"),
    ("prompt", "промпт"),
    ("prompts", "промпты"),
    ("embedding", "эмбеддинг"),
    ("embeddings", "эмбеддинги"),
    ("API", "программный интерфейс"),
    ("GPU", "видеокарта"),
    ("CPU", "процессор"),
    ("cloud", "облако"),
    ("cloud storage", "облачное хранилище"),
    ("software", "программа"),
    ("hardware", "аппаратура"),
    ("framework", "фреймворк"),
    ("library", "библиотека"),

    # Общие слова
    ("capable of", "способный на"),
    ("capable", "способный"),
    ("processing", "обработка"),
    ("training", "обучение"),
    ("inference", "инференс"),
    ("pattern", "шаблон"),
    ("patterns", "шаблоны"),
    ("features", "характеристики"),
    ("feature", "характеристика"),
    ("data", "данные"),
    ("model", "модель"),
    ("models", "модели"),
    ("algorithm", "алгоритм"),
    ("algorithms", "алгоритмы"),
    ("output", "вывод"),
    ("input", "ввод"),
    ("task", "задача"),
    ("tasks", "задачи"),
    ("process", "процесс"),
    ("system", "система"),
    ("systems", "системы"),
    ("approach", "подход"),
    ("research", "исследование"),
    ("researchers", "исследователи"),
    ("project", "проект"),
    ("projects", "проекты"),
    ("research projects", "исследовательские проекты"),

    # Бренды (оставляем, но иногда заменяем)
    ("Assembly AI", "Ассамбли ИИ"),
    ("AssemblyAI", "Ассамбли ИИ"),
    ("OpenAI", "ОпенИИ"),
    ("Google", "Гугл"),
    ("Apple", "Эппл"),
    ("Microsoft", "Майкрософт"),
    ("NVIDIA", "Нвидиа"),
    ("Nvidia", "Нвидиа"),
    ("Tesla", "Тесла"),
    ("Twitter", "Твиттер"),
    ("YouTube", "Ютуб"),
]


def fix_english(text: str) -> str:
    """Заменяет английские слова на русские."""
    if not text:
        return text

    result = text

    # Заменяем фразы (сначала длинные)
    for eng, rus in sorted(REPLACEMENTS, key=lambda x: -len(x[0])):
        # Заменяем с учётом регистра
        # Простой случай: слово целиком
        pattern = r'\b' + re.escape(eng) + r'\b'
        result = re.sub(pattern, rus, result, flags=re.IGNORECASE)

    return result


if __name__ == "__main__":
    tests = [
        "искусственные neural networks могут воспринимать музыку",
        "AI и machine learning — это будущее",
        "large language models capable of processing data",
        "NVIDIA и OpenAI работают над AI",
    ]
    for t in tests:
        print(f"Было:  {t}")
        print(f"Стало: {fix_english(t)}")
        print()