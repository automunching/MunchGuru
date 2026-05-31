import firebase_admin
from firebase_admin import credentials, firestore
import os, json, base64
from dotenv import load_dotenv

load_dotenv()  # This loads your .env file

if not firebase_admin._apps:
    encoded = os.getenv("FIREBASE_CREDENTIALS_BASE64")
    decoded = json.loads(base64.b64decode(encoded))
    cred = credentials.Certificate(decoded)
    firebase_admin.initialize_app(cred)

db = firestore.client()
print("firebase connected")