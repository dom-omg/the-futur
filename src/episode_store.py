import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))


def _client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=str(DATA_DIR / "chroma"),
        settings=Settings(anonymized_telemetry=False),
    )


def _ef():
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def get_episodes_collection():
    return _client().get_or_create_collection("episodes", embedding_function=_ef())


def get_patterns_collection():
    return _client().get_or_create_collection("patterns", embedding_function=_ef())


def log_episode(user_input: str, agent_response: str, context_used: str = "") -> str:
    col = get_episodes_collection()
    episode_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    text = f"USER: {user_input}\nAGENT: {agent_response}"

    col.add(
        documents=[text],
        metadatas=[{
            "timestamp": now,
            "user_input": user_input,
            "agent_response": agent_response,
            "context_used": context_used,
            "date": now[:10],
        }],
        ids=[episode_id],
    )
    return episode_id


def get_recent_episodes(hours: int = 24) -> list[dict]:
    col = get_episodes_collection()
    results = col.get(include=["documents", "metadatas"])
    if not results["ids"]:
        return []

    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    episodes = []
    for i, meta in enumerate(results["metadatas"]):
        ts = datetime.fromisoformat(meta["timestamp"]).timestamp()
        if ts >= cutoff:
            episodes.append({
                "id": results["ids"][i],
                "document": results["documents"][i],
                "meta": meta,
            })

    return sorted(episodes, key=lambda e: e["meta"]["timestamp"])


def get_similar_episodes(query: str, n: int = 5) -> list[dict]:
    col = get_episodes_collection()
    count = col.count()
    if count == 0:
        return []

    results = col.query(
        query_texts=[query],
        n_results=min(n, count),
        include=["documents", "metadatas", "distances"],
    )

    out = []
    for i in range(len(results["ids"][0])):
        out.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "meta": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return out


def store_pattern(pattern_text: str, pattern_type: str, source_date: str) -> str:
    col = get_patterns_collection()
    pattern_id = str(uuid.uuid4())
    col.add(
        documents=[pattern_text],
        metadatas=[{
            "type": pattern_type,
            "source_date": source_date,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }],
        ids=[pattern_id],
    )
    return pattern_id


def get_relevant_patterns(query: str, n: int = 5) -> list[dict]:
    col = get_patterns_collection()
    count = col.count()
    if count == 0:
        return []

    results = col.query(
        query_texts=[query],
        n_results=min(n, count),
        include=["documents", "metadatas", "distances"],
    )

    out = []
    for i in range(len(results["ids"][0])):
        out.append({
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "meta": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return out


def episode_count() -> int:
    return get_episodes_collection().count()


def pattern_count() -> int:
    return get_patterns_collection().count()
