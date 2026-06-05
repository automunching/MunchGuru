from config.firebase_config import db


def get_all_restaurants():
    """
    Fetch all restaurants from Firestore.
    Only picks fields relevant to customer-facing suggestions.
    """
    snapshot = db.collection("restaurants").stream()
    result = []
    for doc in snapshot:
        data = doc.to_dict()
        result.append({
            "id":             doc.id,
            "restaurantName": data.get("restaurantName", ""),
            "branch":         data.get("branch", ""),
            "address":        data.get("address", ""),
            "isOpen":         data.get("isOpen", False),
            "serviceRadius":  data.get("serviceRadius", False),
            
        })
    return result


# from services.restaurants import get_all_restaurants
# from tabulate import tabulate

# restaurants = get_all_restaurants()

# # Convert to table
# print(restaurants)