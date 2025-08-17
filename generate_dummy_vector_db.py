import os
import pickle
import faiss
import numpy as np

# Create folder for vectorstore
os.makedirs("vectorstore", exist_ok=True)

# Example documents (replace with your own later)
documents = [
    "Python is a popular programming language.",
    "FAISS is a library for efficient similarity search.",
    "Streamlit is great for building interactive web apps.",
    "Ollama lets you run LLMs locally.",
    "SentenceTransformers is used for generating embeddings."
]

# Save documents metadata
with open("vectorstore/index.pkl", "wb") as f:
    pickle.dump(documents, f)

# Create dummy random embeddings (same size for each doc)
np.random.seed(42)  # for reproducibility
dimension = 384  # typical dimension for MiniLM models
embeddings = np.random.rand(len(documents), dimension).astype("float32")

# Create FAISS index
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# Save FAISS index
faiss.write_index(index, "vectorstore/index.faiss")

print("✅ Offline vector store built successfully with dummy embeddings!")
