import os
import uuid
import fitz
import faiss
import numpy as np
import requests

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"

headers = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

app = FastAPI(title="PDF RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

sessions = {}

#embedder = SentenceTransformer("all-MiniLM-L6-v2")
embedder = SentenceTransformer(
    "sentence-transformers/paraphrase-MiniLM-L3-v2"
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=30,
)

def extract_text_from_pdf(path):
    doc = fitz.open(path)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    return text

def build_index(chunks):
    embeddings = embedder.encode(
        chunks,
        convert_to_numpy=True
    ).astype("float32")

    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatIP(embeddings.shape[1])

    index.add(embeddings)

    return index

def retrieve(query, index, chunks, top_k=4):
    q = embedder.encode(
        [query],
        convert_to_numpy=True
    ).astype("float32")

    faiss.normalize_L2(q)

    scores, indices = index.search(q, top_k)

    return [chunks[i] for i in indices[0]]

def ask_llm(context, question):
    prompt = f"""
Answer only from the given PDF context.

If answer is not available, say:
"I could not find that in the document."

Context:
{context}

Question:
{question}
"""

    payload = {
        "inputs": prompt
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload
    )

    result = response.json()

    if isinstance(result, list):
        return result[0]["generated_text"]

    return "Model response error."

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF allowed")

    path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"

    with open(path, "wb") as f:
        f.write(await file.read())

    text = extract_text_from_pdf(str(path))

    if not text.strip():
        raise HTTPException(400, "No text extracted")

    chunks = splitter.split_text(text)

    index = build_index(chunks)

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "chunks": chunks,
        "index": index
    }

    return {
        "session_id": session_id,
        "chunks": len(chunks),
        "filename": file.filename
    }

class QueryRequest(BaseModel):
    session_id: str
    question: str

@app.post("/query")
async def query_pdf(req: QueryRequest):
    session = sessions.get(req.session_id)

    if not session:
        raise HTTPException(404, "Session not found")

    top_chunks = retrieve(
        req.question,
        session["index"],
        session["chunks"]
    )

    context = "\n\n".join(top_chunks)

    answer = ask_llm(context, req.question)

    return {
        "answer": answer,
        "sources": top_chunks
    }

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }