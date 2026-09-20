# reindex.py — пересоздание эмбеддингов
import json
import numpy as np
import hashlib
from sentence_transformers import SentenceTransformer

print("[1] Загрузка текстов...")
with open("agent_data/texts.json", "r", encoding="utf-8") as f:
    texts = json.load(f)
print(f"    Документов: {len(texts)}")

print("[2] Загрузка BGE-M3...")
model = SentenceTransformer("BAAI/bge-m3")

print("[3] Создание эмбеддингов...")
embeddings = model.encode(
    texts,
    normalize_embeddings=True,
    show_progress_bar=True,
    batch_size=32,
)
print(f"    Форма: {embeddings.shape}")

print("[4] Сохранение...")
np.save("agent_data/embeddings.npy", embeddings)

hashes = [hashlib.md5(t.encode()).hexdigest() for t in texts]
with open("agent_data/hashes.json", "w", encoding="utf-8") as f:
    json.dump(hashes, f)

print("✅ Готово")
print(f"   embeddings.npy: {embeddings.shape}")
print(f"   hashes.json: {len(hashes)}")