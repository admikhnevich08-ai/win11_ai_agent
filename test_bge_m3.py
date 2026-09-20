# test_bge_m3.py — проверка BGE-M3
import numpy as np
import json
from sentence_transformers import SentenceTransformer

print("[1] Загрузка BGE-M3...")
model = SentenceTransformer("BAAI/bge-m3")
print(f"    Размерность: {model.get_sentence_embedding_dimension()}")

print("[2] Загрузка эмбеддингов базы...")
embeddings = np.load("agent_data/embeddings.npy")
print(f"    Форма: {embeddings.shape}")

print("[3] Загрузка текстов...")
with open("agent_data/texts.json", "r", encoding="utf-8") as f:
    texts = json.load(f)
print(f"    Документов: {len(texts)}")

if embeddings.shape[0] != len(texts):
    print(f"\n⚠️  ВНИМАНИЕ: эмбеддингов {embeddings.shape[0]}, текстов {len(texts)}")
    exit(1)

test_queries = [
    "расскажи про нейросети",
    "что такое искусственный интеллект",
    "погода в Москве",
    "2+2",
    "новости технологий",
    "Python программирование",
    "машинное обучение",
]

print("\n[4] Тест поиска:")
for query in test_queries:
    q_emb = model.encode(query, normalize_embeddings=True)
    scores = np.dot(embeddings, q_emb)
    top_idx = np.argsort(scores)[::-1][:3]
    
    print(f"\n  Запрос: «{query}»")
    for i, idx in enumerate(top_idx):
        score = scores[idx]
        text_preview = texts[idx][:100].replace("\n", " ").replace("\r", " ")
        print(f"    {i+1}. [{score:.3f}] {text_preview}...")

print("\n✅ Готово")