from config.firebase_config import db

def get_all_customers():
    customers = db.collection("customers").stream()

    result = []

    for customer in customers:
        data = customer.to_dict()
        data["id"] = customer.id
        result.append(data)

    return result