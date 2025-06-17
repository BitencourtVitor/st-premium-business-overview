import streamlit as st
import json
import logging
import traceback
from pathlib import Path
from pymongo import MongoClient
from urllib.parse import quote_plus
import importlib.util

# Page config - DEVE SER A PRIMEIRA CHAMADA STREAMLIT
FAVICON = "assets/premium_favicon.png"
LOGO = "assets/premium_logo.png"
st.set_page_config(
    layout="wide",
    page_title="Business Operations Review",
    page_icon=FAVICON,
    initial_sidebar_state="collapsed"
)

from utils.modal_timesheet_analysis import show_manage_modal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if 'user' not in st.session_state:
    st.session_state['user'] = None
    st.session_state['user_data'] = None
    st.session_state['authenticated'] = False

# --- Função para obter a URI do MongoDB via st.secrets ---
def get_mongo_uri():
    username = st.secrets["mongodb"]["username"]
    password = st.secrets["mongodb"]["password"]
    cluster = st.secrets["mongodb"]["cluster"]
    password_escaped = quote_plus(password)
    uri = f"mongodb+srv://{username}:{password_escaped}@{cluster}/?retryWrites=true&w=majority&appName=BusinessOperationsReview"
    return uri
# --------------------------------------------------------

# Função para buscar dados de qualquer collection do MongoDB
def get_collection_data(collection_name):
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri, tls=True, tlsAllowInvalidCertificates=False)
        db = client[st.secrets["mongodb"]["database"]]
        collection = db[collection_name]
        data = list(collection.find({}, {"_id": 0}))
        return data
    except Exception as e:
        logger.error(f"Erro ao carregar dados da coleção '{collection_name}': {e}")
        st.error(f"Erro ao carregar dados da coleção '{collection_name}'.")
        return []

# Função para buscar usuários autorizados (collection 'users')
def get_authorized_users():
    return get_collection_data("users")

# login_user usando a collection 'users'
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
    """Clear session state and logout user"""
    st.session_state['user'] = None
    st.session_state['user_data'] = None
    st.session_state['authenticated'] = False

def show_login():
    """Display login screen"""
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
    """Display header with logo and user info"""
    st.logo(LOGO)
    col1, col2 = st.columns([2.5, 0.1])

    with col1:
        st.header("Business Operations Review", divider="blue")
        st.markdown(f"*What matters isn't the company's mistakes, but how it responds to them.*")
        st.caption(st.session_state['user_data']['name'])
    with col2:
        if st.session_state['user_data']:
            if st.button(":material/logout:", help="Clique para sair", type='secondary'):
                logout_user()
                st.rerun()

def show_edit_profile_modal():
    """Display modal for editing user profile usando st.modal nativo"""
    with st.modal("Edit Profile", width="medium"):
        current_user = st.session_state['user_data']
        current_name = current_user['name']
        with st.form("edit_profile_form"):
            new_name = st.text_input("Name", value=current_name)
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            submitted = st.form_submit_button("Save Changes")
            if submitted:
                if new_password and new_password != confirm_password:
                    st.error("Passwords do not match!")
                    return
                try:
                    with open("utils/authorized_users.json", "r", encoding='utf-8') as file:
                        data = json.load(file)
                    for user in data["users"]:
                        if user["login"] == current_user["login"]:
                            user["name"] = new_name
                            if new_password:
                                user["password"] = new_password
                            break
                    with open("utils/authorized_users.json", "w", encoding='utf-8') as file:
                        json.dump(data, file, indent=4)
                    st.session_state['user_data']['name'] = new_name
                    if new_password:
                        st.session_state['user_data']['password'] = new_password
                    st.success("Profile updated successfully!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Error updating profile: {str(e)}")
                    st.error("Error updating profile. Please try again.")

def show_main_content():
    """Display main content based on user roles and screens"""
    user_data = st.session_state['user_data']
    if not user_data:
        return

    # Load available screens from JSON
    try:
        available_screens_data = get_collection_data("screens")
        # Create mapping only for title->description
        screen_mapping = {screen['title']: screen.get('description', screen['title']) for screen in available_screens_data}
    except Exception as e:
        logger.error(f"Erro ao carregar telas disponíveis do banco: {e}")
        st.error("Erro ao carregar configuração de telas disponíveis.")
        return

    # Get available screens for user
    user_screens = user_data.get('screens', [])
    if not user_screens:
        st.warning("Nenhuma tela disponível para seu perfil.")
        return

    # screens = ... (lista vinda do banco)
    valid_screens = []
    for screen in user_screens:
        module_path = f"pages.{screen}"
        if importlib.util.find_spec(module_path):
            valid_screens.append(screen)

    # Create tabs for available screens using descriptions from JSON
    tab_titles = [screen_mapping.get(screen, screen) for screen in valid_screens]
    tabs = st.tabs(tab_titles)
    
    # Load and display each screen's content
    for tab, screen in zip(tabs, valid_screens):
        with tab:
            try:
                # The screen title is now the same as the module name
                module_name = screen
                logger.info(f"Tentando carregar módulo: pages.{module_name}")
                
                # Check if module file exists
                module_path = Path(f"pages/{module_name}.py")
                if not module_path.exists():
                    raise FileNotFoundError(f"Arquivo do módulo não encontrado: {module_path}")
                
                # Dynamically import the screen module
                module = __import__(f"pages.{module_name}", fromlist=['show_screen'])
                if not hasattr(module, 'show_screen'):
                    raise AttributeError(f"Módulo {module_name} não possui função show_screen")
                
                module.show_screen(user_data)
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Erro ao carregar módulo {screen}: {str(e)}\n{error_details}")
                st.error(f"Erro ao carregar módulo {screen}: {str(e)}")
                if st.checkbox("Mostrar detalhes do erro", key=f"show_error_details_{screen}"):
                    st.code(error_details)

# Main application flow
if not st.session_state['authenticated']:
    show_login()
else:
    show_header()
    show_main_content()