# -*- coding: utf-8 -*-
"""
Локальная LLM через llama.cpp (GGUF, int4).
Qwen2.5-7B-Instruct-Q4_K_M — 2 части.
"""
import time
from llama_cpp import Llama


# Указываем ПЕРВУЮ часть — llama.cpp сам найдёт вторую
MODEL_PATH = "models/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"


class LocalLLM_GGUF:
    """Qwen 7B Q4 через llama.cpp."""

    def __init__(self, model_path=MODEL_PATH):
        print(f"[llm] Загрузка: {model_path}")
        t0 = time.time()

        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=8,
            n_gpu_layers=0,
            verbose=False,
        )

        self.model_name = "Qwen2.5-7B-Instruct-Q4_K_M"
        print(f"[llm] Загружено за {time.time() - t0:.1f} сек")

    def _build_prompt(self, question, context):
        system = (
            "Ты — русскоязычный ассистент. Отвечай ИСКЛЮЧИТЕЛЬНО на русском языке. "
            "СТРОГО ЗАПРЕЩЕНО использовать любые английские слова, фразы, термины. "
            "Если в контексте встретилось английское слово — переведи его на русский. "
            "ВАЖНО: в контексте могут быть документы на разные темы. "
            "Используй ТОЛЬКО те, что ПРЯМО ОТНОСЯТСЯ к вопросу. "
            "Игнорируй всё, что не по теме — даже если оно есть в контексте. "
            "Если пользователь просит подробнее — углубись в детали. "
            "НЕ повторяй предыдущий ответ дословно. "
            "Добавь НОВЫЕ факты из контекста. "
            "Используй ТОЛЬКО факты из предоставленного контекста. "
            "НЕ используй свои общие знания. НЕ додумывай. НЕ придумывай факты. "
            "Если в контексте нет чёткого ответа на вопрос — ответь ровно так: "
            "«В собранных данных нет информации по этому вопросу». "
            "Не пытайся угадать. Не добавляй ничего от себя. "
            "ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ. НИ ОДНОГО АНГЛИЙСКОГО СЛОВА."
        )
        return (
            f"<|im_start|>system\n{system}<|im_end|>\n"
            f"<|im_start|>user\nКонтекст:\n{context}\n\n"
            f"Вопрос: {question}\n\n"
            f"Ответь на русском языке. Начни ответ так:\n"
            f"«Согласно собранной информации,»<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    @staticmethod
    def _clean(text):
        import re
        text = re.sub(
            r'^[\s"\'«»]*[Сс]огласно\s+собранной\s+информации[\s,"\'»]*',
            '',
            text,
            count=1,
        )
        text = re.sub(
            r'^[\s"\'«»]*[Оо]твет\s*(на\s+русском)?\s*:\s*',
            '',
            text,
            count=1,
        )
        text = text.strip()

        try:
            from text_fixes import fix_english
            text = fix_english(text)
        except ImportError:
            pass

        return text

    def answer(self, question, context, stream=True, max_new_tokens=500, temperature=0.4):
        prompt = self._build_prompt(question, context)

        out = self.llm(
            prompt,
            max_tokens=max_new_tokens,
            temperature=temperature,
            top_p=0.9,
            repeat_penalty=1.2,
            stop=["<|im_end|>", "<|im_start|>"],
            echo=False,
        )

        text = out["choices"][0]["text"].strip()
        text = self._clean(text)

        if stream:
            print(text)

        return text

    def generate(self, prompt, max_tokens=100, temperature=0.0, stop=None):
        """Прямая генерация — для planner / react_agent."""
        out = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop or ["\n\n", "<|im_end|>"],
            echo=False,
        )
        return out["choices"][0]["text"].strip()

    @property
    def pipe(self):
        """Адаптер для совместимости с transformers pipeline."""
        class _PipeAdapter:
            def __init__(self, llm):
                self.llm = llm

            def __call__(self, prompt, **kwargs):
                if isinstance(prompt, list):
                    parts = []
                    for msg in prompt:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
                    parts.append("<|im_start|>assistant\n")
                    prompt = "\n".join(parts)

                text = self.llm.generate(
                    prompt,
                    max_tokens=kwargs.get("max_new_tokens", 300),
                    temperature=kwargs.get("temperature", 0.1),
                )
                return [{"generated_text": text}]

        return _PipeAdapter(self)


if __name__ == "__main__":
    print("Загрузка...")
    llm = LocalLLM_GGUF()
    print("\nТест:")
    result = llm.answer(
        "расскажи про нейросети",
        "Нейросети — это математические модели, которые обучаются на данных."
    )
    print(f"\n---\n{result}")