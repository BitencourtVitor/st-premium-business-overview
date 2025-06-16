from pymongo import MongoClient
import streamlit as st

def capitalize_name(name):
    return " ".join(word.capitalize() for word in name.split())

client = MongoClient(st.secrets["mongodb"]["uri"])
db = client[st.secrets["mongodb"]["database"]]

for collection_name in ["timesheet_analysis_data", "timesheet_analysis_employees"]:
    collection = db[collection_name]
    
    for doc in collection.find({"Nome": {"$exists": True}}):
        nome_original = doc["Nome"]
        nome_corrigido = capitalize_name(nome_original)
        
        if nome_corrigido != nome_original:
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"Nome": nome_corrigido}}
            )

print("Atualização concluída.")
