import streamlit as st
from pymongo import MongoClient
from urllib.parse import quote_plus
from bson import ObjectId

def get_mongo_uri():
    username = st.secrets["mongodb"]["username"]
    password = st.secrets["mongodb"]["password"]
    cluster = st.secrets["mongodb"]["cluster"]
    password_escaped = quote_plus(password)
    uri = f"mongodb+srv://{username}:{password_escaped}@{cluster}/?retryWrites=true&w=majority&appName=BusinessOperationsReview&tls=true&tlsAllowInvalidCertificates=false"
    return uri

def get_users_by_role(role):
    """Busca todos os usuários que possuem uma determinada role"""
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri, tls=True, tlsAllowInvalidCertificates=False)
        db = client[st.secrets["mongodb"]["database"]]
        users_collection = db['users']
        
        # Buscar usuários que possuem a role especificada
        users = list(users_collection.find({"roles": role}))
        
        # Log para debug
        print(f"Encontrados {len(users)} usuários com role '{role}'")
        for user in users:
            print(f"  - {user.get('name', 'Sem nome')} (ID: {user.get('_id')})")
        
        return [str(user["_id"]) for user in users]
    except Exception as e:
        st.error(f"Erro ao buscar usuários por role '{role}': {e}")
        return []

def get_collection_data(collection_name, include_id=False, user_role_filter=None):
    """
    Carrega dados de uma coleção com filtro opcional por role de usuário
    
    Args:
        collection_name: Nome da coleção
        include_id: Se deve incluir o _id dos documentos
        user_role_filter: Role para filtrar usuários (ex: 'permits_admin', 'timesheet_admin')
    """
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri, tls=True,tlsAllowInvalidCertificates=False)
        db = client[st.secrets["mongodb"]["database"]]
        collection = db[collection_name]
        
        # Se há filtro por role, buscar usuários com essa role
        if user_role_filter:
            user_ids = get_users_by_role(user_role_filter)
            if user_ids:
                # Converter strings para ObjectId
                user_object_ids = [ObjectId(user_id) for user_id in user_ids]
                # Filtrar documentos que têm user_id na lista de usuários com a role
                filter_query = {"user_id": {"$in": user_object_ids}}
            else:
                # Se não há usuários com a role, retornar lista vazia
                return []
        else:
            filter_query = {}
        
        if include_id:
            data = list(collection.find(filter_query))
        else:
            data = list(collection.find(filter_query, {"_id": 0}))
        return data
    except Exception as e:
        st.error(f"Erro ao carregar dados da coleção '{collection_name}': {e}")
        return []

def get_collection_data_by_area(collection_name, include_id=False, area_filter=None):
    """
    Carrega dados de uma coleção com filtro por área/tab
    
    Args:
        collection_name: Nome da coleção
        include_id: Se deve incluir o _id dos documentos
        area_filter: Área para filtrar (ex: 'timesheet', 'permit')
    """
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri, tls=True, tlsAllowInvalidCertificates=False)
        db = client[st.secrets["mongodb"]["database"]]
        collection = db[collection_name]
        
        # Se há filtro por área, filtrar documentos por essa área
        if area_filter:
            # Para dados existentes que não têm campo 'area', usar filtro por role do usuário
            if area_filter == 'timesheet':
                user_ids = get_users_by_role('timesheet_admin')
            elif area_filter == 'permit':
                user_ids = get_users_by_role('permits_admin')
            else:
                user_ids = []
            
            if user_ids:
                # Converter strings para ObjectId
                user_object_ids = [ObjectId(user_id) for user_id in user_ids]
                # Filtrar por área OU por user_id (para dados existentes)
                filter_query = {
                    "$or": [
                        {"area": area_filter},
                        {"user_id": {"$in": user_object_ids}}
                    ]
                }
            else:
                # Se não há usuários com a role, filtrar apenas por área
                filter_query = {"area": area_filter}
        else:
            filter_query = {}
        
        if include_id:
            data = list(collection.find(filter_query))
        else:
            data = list(collection.find(filter_query, {"_id": 0}))
        
        # Log para debug
        print(f"Coleção '{collection_name}' - Filtro: {area_filter} - Encontrados: {len(data)} documentos")
        
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

def get_user_name(user_id):
    """Busca o nome do usuário na collection 'users' pelo user_id"""
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri, tls=True, tlsAllowInvalidCertificates=False)
        db = client[st.secrets["mongodb"]["database"]]
        users_collection = db['users']
        
        # Converter user_id para ObjectId se for string, ou usar diretamente se já for ObjectId
        if isinstance(user_id, str):
            try:
                user_id_obj = ObjectId(user_id)
            except:
                return 'ID de usuário inválido'
        else:
            user_id_obj = user_id
            
        user = users_collection.find_one({"_id": user_id_obj})
        
        if user:
            return user.get('name', 'Usuário não encontrado')
        else:
            return 'Usuário não encontrado'
    except Exception as e:
        st.error(f"Erro ao buscar usuário: {e}")
        return 'Erro ao buscar usuário' 