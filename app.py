import streamlit as st
import json
import logging
import traceback
from pathlib import Path
from pymongo import MongoClient
from urllib.parse import quote_plus

# Page config - DEVE SER A PRIMEIRA CHAMADA STREAMLIT
FAVICON = "assets/premium_favicon.png"
LOGO = "assets/premium_logo.png"
st.set_page_config(
    layout="wide",
    page_title="Business Overview",
    page_icon=FAVICON,
    initial_sidebar_state="collapsed"
)

from utils.modal_admin_timesheet_analysis import modal
from utils.user_change_data import user_change_data_modal

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
    uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=BusinessOperationsReview"
    return uri
# --------------------------------------------------------

# Função para buscar dados de qualquer collection do MongoDB
def get_collection_data(collection_name):
    try:
        uri = get_mongo_uri()
        client = MongoClient(uri)
        db = client[st.secrets["mongodb"]["database"]]
        collection = db[collection_name]
        data = list(collection.find({}, {"_id": 0}))
        return data
    except Exception as e:
        logger.error(f"Error loading data from MongoDB collection '{collection_name}': {e}")
        st.error(f"Error loading data from collection '{collection_name}'.")
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
        st.header("Business Operations Review | Login", divider="blue")
        with st.container(border=True):
            st.header("Login")
            st.write("Please enter your corporate email to access the platform.")
            email = st.text_input("Email", key="email", placeholder="Enter your email")
            password = st.text_input("Password", key="password", placeholder="Insert your password", type="password")
            if st.button("Enter", key="enter_button"):
                if login_user(email, password):
                    st.rerun()
                else:
                    st.error("Login not authorized.")
    with col2:
        st.empty()

def show_header():
    """Display header with logo and user info"""
    st.logo(LOGO)
    col1, col2, col3 = st.columns([2.5, 0.1, 0.1])

    with col1:
        st.subheader("Business Operations Review | Welcome, " + st.session_state['user_data']['name'])
    with col2:
        if st.session_state['user_data']:
            if st.button(":material/settings:", help="Edit profile", type='secondary', disabled=True):
                user_change_data_modal()
    with col3:
        if st.session_state['user_data']:
            if st.button(":material/logout:", help="Click to logout", type='secondary'):
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
        with open("utils/available_screens.json", "r", encoding='utf-8') as file:
            available_screens_data = json.load(file)
            # Create mapping only for title->description
            screen_mapping = {screen['title']: screen['description'] for screen in available_screens_data['screens']}
    except Exception as e:
        logger.error(f"Error loading available screens: {e}")
        st.error("Error loading available screens configuration.")
        return

    # Get available screens for user
    user_screens = user_data.get('screens', [])
    if not user_screens:
        st.warning("No screens available for your role.")
        return

    # Create tabs for available screens using descriptions from JSON
    tab_titles = [screen_mapping.get(screen, screen) for screen in user_screens]
    tabs = st.tabs(tab_titles)
    
    # Load and display each screen's content
    for tab, screen in zip(tabs, user_screens):
        with tab:
            try:
                # The screen title is now the same as the module name
                module_name = screen
                logger.info(f"Attempting to load module: pages.{module_name}")
                
                # Check if module file exists
                module_path = Path(f"pages/{module_name}.py")
                if not module_path.exists():
                    raise FileNotFoundError(f"Module file not found: {module_path}")
                
                # Dynamically import the screen module
                module = __import__(f"pages.{module_name}", fromlist=['show_screen'])
                if not hasattr(module, 'show_screen'):
                    raise AttributeError(f"Module {module_name} does not have show_screen function")
                
                module.show_screen(user_data)
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(f"Error loading {screen} module: {str(e)}\n{error_details}")
                st.error(f"Error loading {screen} module: {str(e)}")
                if st.checkbox("Show error details"):
                    st.code(error_details)

# Main application flow
if not st.session_state['authenticated']:
    show_login()
else:
    show_header()
    show_main_content()
    # TESTE: Mostra todos os usuários da collection 'users' após login
    st.info("Usuários cadastrados na collection 'users':")
    st.write(get_authorized_users())