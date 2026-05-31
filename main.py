import os
import json
import base64
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from rag.retriever import build_vector_store, retrieve_relevant_food

load_dotenv()

app = FastAPI()

# Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load rules
with open("rules.txt", "r") as f:
    RULES = f.read()

# Build vector store on startup
@app.on_event("startup")
async def startup_event():
    build_vector_store()
    print("✅ Vector store built")

# In-memory history per session (simple version)
conversation_history = []

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

# Store histories per session
sessions: dict = {}

@app.get("/")
def root():
    return {"status": "AutoMunch AI is running 🍔"}

@app.post("/chat")
def chat(req: ChatRequest):
    session_id = req.session_id
    user_input = req.message.strip()

    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id]

    # RAG: find top 2 relevant menu items
    results = retrieve_relevant_food(user_input, top_k=2)
    context = "\n\n".join(r["text"] for r in results) if results else "No matching items found."

    history.append({"role": "user", "content": user_input})

    messages = [
        {"role": "system", "content": RULES},
        {"role": "system", "content": f"Relevant food options from our menu:\n\n{context}"},
        *history
    ]

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=messages,
        temperature=0.7,
        max_tokens=500,
    )

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})

    # Keep last 20 turns
    if len(history) > 20:
        sessions[session_id] = history[-20:]

    return {"reply": reply}