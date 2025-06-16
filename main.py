import streamlit as st
import json
import logging
import traceback
from pathlib import Path

# Configuração da página
FAVICON = "assets/premium_favicon.png"
LOGO = "assets/premium_logo.png"
st.set_page_config(
    page_title="Business Operations Review",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon=FAVICON
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar session_state
if 'user' not in st.session_state:
    st.session_state['user'] = None
    st.session_state['user_data'] = None
    st.session_state['authenticated'] = False

def get_mongo_uri():
    username = st.secrets["mongodb"]["username"]
    password = st.secrets["mongodb"]["password"]
    cluster = st.secrets["mongodb"]["cluster"]
    from urllib.parse import quote_plus
    password_escaped = quote_plus(password)
    uri = f"mongodb+srv://{username}:{password_escaped}@{cluster}/?retryWrites=true&w=majority&appName=BusinessOperationsReview"
    return uri

def get_collection_data(collection_name):
    try:
        from pymongo import MongoClient
        uri = get_mongo_uri()
        client = MongoClient(uri)
        db = client[st.secrets["mongodb"]["database"]]
        collection = db[collection_name]
        data = list(collection.find({}, {"_id": 0}))
        return data
    except Exception as e:
        logger.error(f"Erro ao carregar dados da coleção '{collection_name}': {e}")
        st.error(f"Erro ao carregar dados da coleção '{collection_name}'.")
        return []

def get_screens():
    """Busca todas as telas disponíveis na collection 'screens'"""
    return get_collection_data("screens")

def get_authorized_users():
    return get_collection_data("users")

def login_user(email: str, password: str) -> bool:
    authorized_users = get_authorized_users()
    user = next((u for u in authorized_users if u["login"] == email and u["password"] == password), None)
    if user:
        st.session_state['user'] = email
        st.session_state['user_data'] = user
        st.session_state['authenticated'] = True
        return True
    return False

def logout_user():
    st.session_state['user'] = None
    st.session_state['user_data'] = None
    st.session_state['authenticated'] = False

def show_login():
    st.logo(LOGO)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.header("Business Operations Review", divider="blue")
        with st.container(border=True):
            st.header("Login")
            st.write("Acesse com seu e-mail corporativo.")
            email = st.text_input("Email", key="email", placeholder="Digite seu e-mail")
            senha = st.text_input("Senha", key="senha", placeholder="Digite sua senha", type="password")
            if st.button("Entrar", key="entrar_button"):
                if login_user(email, senha):
                    st.rerun()
                else:
                    st.error("Login não autorizado.")
    with col2:
        st.empty()

def show_header():
    st.logo(LOGO)
    col1, col2 = st.columns([2.5, 0.1])
    with col1:
        st.header("Business Operations Review", divider="blue")
        st.caption(st.session_state['user_data']['name'])
    with col2:
        if st.session_state['user_data']:
            if st.button(":material/logout:", help="Clique para sair", type='secondary'):
                logout_user()
                st.rerun()

def show_main_content():
    user_data = st.session_state['user_data']
    if not user_data:
        return
    try:
        available_screens_data = get_screens()
        # Espera-se que cada documento tenha 'title' e 'description'
        screen_mapping = {screen['title']: screen.get('description', screen['title']) for screen in available_screens_data}
    except Exception as e:
        logger.error(f"Erro ao carregar telas disponíveis do banco: {e}")
        st.error("Erro ao carregar configuração de telas disponíveis.")
        return
    user_screens = user_data.get('screens', [])
    if not user_screens:
        st.warning("Nenhuma tela disponível para seu perfil.")
        return
    tab_titles = [screen_mapping.get(screen, screen) for screen in user_screens]
    tabs = st.tabs(tab_titles)
    for tab, screen in zip(tabs, user_screens):
        with tab:
            try:
                module_name = screen
                logger.info(f"Tentando carregar módulo: pages.{module_name}")
                module_path = Path(f"pages/{module_name}.py")
                if not module_path.exists():
                    raise FileNotFoundError(f"Arquivo do módulo não encontrado: {module_path}")
                module = __import__(f"pages.{module_name}", fromlist=['show_screen'])
                if not hasattr(module, 'show_screen'):
                    raise AttributeError(f"Módulo {module_name} não possui função show_screen")
                module.show_screen(user_data)
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Erro ao carregar módulo {screen}: {str(e)}\n{error_details}")
                st.error(f"Erro ao carregar módulo {screen}: {str(e)}")
                if st.checkbox("Mostrar detalhes do erro"):
                    st.code(error_details)

if not st.session_state['authenticated']:
    show_login()
else:
    show_header()
    show_main_content()