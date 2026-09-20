# text_fixes_v2.py — расширенная постобработка
import re

def clean_llm_output(text: str) -> str:
    """Чистит вывод LLM от мусора."""
    if not text:
        return text
    
    # 1. Убираем китайские символы
    text = re.sub(r'[\u4e00-\u9fff]+', '', text)
    
    # 2. Убираем японские символы
    text = re.sub(r'[\u3040-\u30ff]+', '', text)
    
    # 3. Убираем корейские символы
    text = re.sub(r'[\uac00-\ud7af]+', '', text)
    
    # 4. Убираем маркеры ACTION/FINAL внутри ответа
    for marker in ["ACTION:", "FINAL:", "ARG:", "TOOL:"]:
        pos = text.find(marker)
        if pos > 20:  # если маркер не в начале
            text = text[:pos].strip()
    
    # 5. Убираем повторяющиеся пробелы
    text = re.sub(r'\s+', ' ', text)
    
    # 6. Убираем незавершённые предложения в конце
    # (если последний символ не ., !, ?, ...)
    text = text.strip()
    if text and text[-1] not in '.!?…':
        # Ищем последнюю точку
        last_dot = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
        if last_dot > len(text) * 0.7:  # если точка не слишком рано
            text = text[:last_dot + 1]
    
    return text.strip()


if __name__ == "__main__":
    tests = [
        "Python — это язык. Pandas для处理中...",
        "Нейросети — это модели. ACTION: search('ещё') FINAL: продолжение",
        "Ответ обрывается на полуслов",
        "Нормальный ответ с точкой.",
    ]
    
    for t in tests:
        print(f"\nВход: {t}")
        print(f"Выход: {clean_llm_output(t)}")