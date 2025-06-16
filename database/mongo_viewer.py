import streamlit as st
from pymongo import MongoClient
from urllib.parse import quote_plus
import pandas as pd

st.set_page_config(page_title="MongoDB Collections Viewer", layout="wide")
st.title("MongoDB Collections Viewer")

# --- Estrutura de conexão do MongoDB ---
username = st.secrets["mongodb"]["username"]
password = st.secrets["mongodb"]["password"]
cluster = st.secrets["mongodb"]["cluster"]
uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=BusinessOperationsReview"
# --------------------------------------

# Conectar ao MongoDB
try:
    client = MongoClient(uri)
    st.success("Conexão com MongoDB estabelecida!")
except Exception as e:
    st.error(f"Erro ao conectar no MongoDB: {e}")
    st.stop()

# Listar todos os bancos de dados
st.header("Bancos de Dados Disponíveis")
db_names = client.list_database_names()
st.write(db_names)

# Selecionar banco de dados
selected_db = st.selectbox("Selecione o banco de dados para inspecionar:", db_names)
db = client[selected_db]

# Listar todas as collections do banco selecionado
st.header(f"Collections em '{selected_db}'")
collection_names = db.list_collection_names()
st.write(collection_names)

# Selecionar collection
selected_collection = st.selectbox("Selecione a collection para visualizar:", collection_names)
collection = db[selected_collection]

# Exibir documentos da collection selecionada
st.header(f"Documentos em '{selected_collection}'")
docs = list(collection.find())

# Se houver user_id, buscar o nome do usuário na collection 'users'
if docs and any('user_id' in doc for doc in docs) and 'users' in collection_names:
    users_coll = db['users']
    user_map = {str(u['_id']): u.get('name', '') for u in users_coll.find()}
    for doc in docs:
        if 'user_id' in doc:
            user_id_str = str(doc['user_id'])
            doc['user_name'] = user_map.get(user_id_str, '(não encontrado)')

if not docs:
    st.info("Nenhum documento encontrado.")
else:
    # Para a tabela, só mostrar campos simples (não dict/list)
    def flatten_doc(doc):
        flat = {}
        for k, v in doc.items():
            if isinstance(v, (dict, list)):
                continue
            flat[k] = v
        return flat
    flat_docs = [flatten_doc(doc) for doc in docs]
    df = pd.DataFrame(flat_docs)
    st.dataframe(df, use_container_width=True)

    # Mostrar campos aninhados (dict/list) em expansores por documento
    for idx, doc in enumerate(docs):
        nested_fields = {k: v for k, v in doc.items() if isinstance(v, (dict, list))}
        if nested_fields:
            with st.expander(f"Ver campos aninhados do documento {idx+1} (_id: {doc.get('_id','')})"):
                st.json(nested_fields) 