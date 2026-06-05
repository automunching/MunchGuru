import os
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from services.menu import get_all_menu
from services.restaurants import get_all_restaurants

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ─── In-memory vector store ───────────────────────────────────────────────────
# Each entry: { "id": str, "text": str, "embedding": List[float], "meta": dict }
VECTOR_STORE: list[dict] = []


# ─── Helpers ──────────────────────────────────────────────────────────────────

def cosine_similarity(a, b) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def create_embedding(text: str) -> list:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def _build_document_text(item: dict, restaurant: dict) -> str:
    radius = restaurant.get("serviceRadius", "Not specified")
    radius_text = f"{radius} meters" if isinstance(radius, (int, float)) else str(radius)
    return (
        f"Food Name: {item.get('name', '')}\n"
        f"Category: {item.get('category', '')}\n"
        f"Description: {item.get('description', '')}\n"
        f"Price: {item.get('price', '')}\n"
        f"Stock: {item.get('stock', 'In Stock')}\n"
        f"Restaurant: {restaurant.get('restaurantName', 'Unknown')}\n"
        f"Branch: {restaurant.get('branch', '')}\n"
        f"Address: {restaurant.get('address', '')}\n"
        f"Service Radius: {radius_text}\n"
        f"Open Now: {'Yes' if restaurant.get('isOpen') else 'No'}"
    )


# ─── Build / rebuild entire store (run once at startup) ───────────────────────

def build_vector_store():
    """
    Fetches all available menu items + their restaurants,
    embeds each one, and stores in VECTOR_STORE.
    Call ONCE on app startup.
    """
    global VECTOR_STORE
    print("🔄 Building embeddings cache…")

    menu_items   = get_all_menu()
    restaurants  = get_all_restaurants()
    restaurant_map = {r["id"]: r for r in restaurants}

    VECTOR_STORE = []
    skipped = 0

    for item in menu_items:
        # Skip unavailable / out-of-stock items
        if not item.get("available", True):
            skipped += 1
            continue
        if item.get("stock", "In Stock").lower() == "out of stock":
            skipped += 1
            continue

        restaurant = restaurant_map.get(item["restaurantId"], {})

        # Skip items whose restaurant is closed
        if not restaurant.get("isOpen", True):
            skipped += 1
            continue

        text      = _build_document_text(item, restaurant)
        embedding = create_embedding(text)

        VECTOR_STORE.append({
            "id":        item["id"],
            "text":      text,
            "embedding": embedding,
            "meta": {
                "name":           item.get("name"),
                "price":          item.get("price"),
                "restaurantName": restaurant.get("restaurantName"),
                "branch":         restaurant.get("branch"),
            }
        })

    print(f"✅ Embeddings ready — {len(VECTOR_STORE)} items indexed, {skipped} skipped")


# ─── Incremental upsert (call from Firebase Cloud Function webhook) ────────────

def upsert_menu_item(item: dict):
    """
    Add or update a single menu item in the vector store.
    Called when Firebase detects a write on the 'menu' collection.
    """
    restaurants = get_all_restaurants()
    restaurant_map = {r["id"]: r for r in restaurants}
    restaurant = restaurant_map.get(item.get("restaurantId", ""), {})

    # Remove old entry for this id if it exists
    remove_menu_item(item["id"])

    # Only index if available
    if not item.get("available", True):
        print(f"⚠️  Item {item['id']} skipped (unavailable)")
        return

    text      = _build_document_text(item, restaurant)
    embedding = create_embedding(text)

    VECTOR_STORE.append({
        "id":        item["id"],
        "text":      text,
        "embedding": embedding,
        "meta": {
    "name":            item.get("name"),
    "price":           item.get("price"),
    "restaurantName":  restaurant.get("restaurantName"),
    "branch":          restaurant.get("branch"),
    "serviceRadius":   restaurant.get("serviceRadius"),   # ADD THIS
}
    })
    print(f"✅ Upserted item: {item.get('name')} ({item['id']})")


def remove_menu_item(item_id: str):
    """Remove a menu item from the vector store by its Firestore doc ID."""
    global VECTOR_STORE
    before = len(VECTOR_STORE)
    VECTOR_STORE = [d for d in VECTOR_STORE if d["id"] != item_id]
    if len(VECTOR_STORE) < before:
        print(f"🗑️  Removed item {item_id} from vector store")


# ─── Query ────────────────────────────────────────────────────────────────────

def retrieve_relevant_food(user_query: str, top_k: int = 2) -> list[dict]:
    """
    Embed the user query and return the top_k most similar menu items.
    """
    if not VECTOR_STORE:
        return []

    query_embedding = create_embedding(user_query)

    scored = sorted(
        VECTOR_STORE,
        key=lambda doc: cosine_similarity(query_embedding, doc["embedding"]),
        reverse=True
    )
    return scored[:top_k]
