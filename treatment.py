from pymongo import MongoClient
from bson import ObjectId
import streamlit as st

username = st.secrets["mongodb"]["username"]
password = st.secrets["mongodb"]["password"]
cluster = st.secrets["mongodb"]["cluster"]
client = MongoClient(f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=BusinessOperationsReview")  # ou sua URL de conexão
db = client['BusinessOperationReview']  # substitui aqui pelo nome do banco

db.monthly_opportunities.insert_one({
    "user_id": ObjectId('684c170b4360684381d223d6'),
    "year": 2025,
    "month": 6,
    "opportunity_list": [
        {
            "challenges": ["Falta de padrão nas justificativas de ausência"],
            "improvements": [
                "Criar modelo fixo para justificativas",
                "Orientar equipe sobre uso do sistema"
            ],
            "title": "Despadronização"
        }
    ]
})