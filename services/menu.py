from config.firebase_config import db


def get_all_menu():
    """
    Fetch all menu items from Firestore.
    Only picks fields relevant to customer-facing suggestions.
    """
    snapshot = db.collection("menu").stream()
    result = []
    for doc in snapshot:
        data = doc.to_dict()
        result.append({
            "id":           doc.id,
            "name":         data.get("name", ""),
            "description":  data.get("description", ""),
            "category":     data.get("category", ""),
            "price":        data.get("price", ""),
            "available":    data.get("available", True),
            "stock":        data.get("stock", "In Stock"),
            "restaurantId": data.get("restaurantId", ""),
        })
    return result
