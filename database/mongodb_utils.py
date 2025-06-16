import streamlit as st
from pymongo import MongoClient
from urllib.parse import quote_plus

def get_mongo_uri():
    username = st.secrets["mongodb"]["username"]
    password = st.secrets["mongodb"]["password"]
    cluster = st.secrets["mongodb"]["cluster"]
    password_escaped = quote_plus(password)
    uri = f"mongodb+srv://{username}:{password_escaped}@{cluster}/?retryWrites=true&w=majority&appName=BusinessOperationsReview&tls=true&tlsAllowInvalidCertificates=false"
    return uri

def get_collection_data(collection_name):
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri, tls=True,tlsAllowInvalidCertificates=False)
        db = client[st.secrets["mongodb"]["database"]]
        collection = db[collection_name]
        data = list(collection.find({}, {"_id": 0}))
        return data
    except Exception as e:
        st.error(f"Erro ao carregar dados da coleção '{collection_name}': {e}")
        return [] 