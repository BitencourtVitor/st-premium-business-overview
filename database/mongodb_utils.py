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

def insert_document(collection_name, document):
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri, tls=True, tlsAllowInvalidCertificates=False)
        db = client[st.secrets["mongodb"]["database"]]
        collection = db[collection_name]
        result = collection.insert_one(document)
        return str(result.inserted_id)
    except Exception as e:
        st.error(f"Erro ao inserir documento na coleção '{collection_name}': {e}")
        return None

def update_document(collection_name, filter_query, update_fields):
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri, tls=True, tlsAllowInvalidCertificates=False)
        db = client[st.secrets["mongodb"]["database"]]
        collection = db[collection_name]
        result = collection.update_one(filter_query, {"$set": update_fields})
        return result.modified_count > 0
    except Exception as e:
        st.error(f"Erro ao atualizar documento na coleção '{collection_name}': {e}")
        return False

def delete_document(collection_name, filter_query):
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri, tls=True, tlsAllowInvalidCertificates=False)
        db = client[st.secrets["mongodb"]["database"]]
        collection = db[collection_name]
        result = collection.delete_one(filter_query)
        return result.deleted_count > 0
    except Exception as e:
        st.error(f"Erro ao remover documento da coleção '{collection_name}': {e}")
        return False 