import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DOCUMENT_ID = "1_BZtDLtDggKQ_2D-5O_JP53z8eKdWSZxbjD8DnJBDlM"
GID_T1 = "814204999"
GID_T2 = "624482067"

def get_url(gid):
    return f"https://docs.google.com/spreadsheets/d/{DOCUMENT_ID}/export?format=xlsx&gid={gid}"

@st.cache_data(ttl=600)
def load_data():
    try:
        df_t1 = pd.read_excel(get_url(GID_T1), engine="openpyxl")
        df_t2 = pd.read_excel(get_url(GID_T2), engine="openpyxl")

        df_t1 = df_t1.rename(columns={
            "Date": "date_t1",
            "Nome": "nome_t1",
            "Error": "error_t1",
            "Team": "team_t1",
            "Corporation": "corporation_t1",
            "Payrate": "payrate_t1",
            "Add time/hour": "add_time_hour_t1",
            "Remove time/hour": "remove_time_hour_t1",
            "ADD $": "add_value_t1",
            "REMOVE $": "remove_value_t1",
            "TOTAL": "total_t1"
        })

        df_t2 = df_t2.rename(columns={
            "Nome": "nome_t2",
            "Empresa": "empresa_t2",
            "USD/hours": "usd_hours_t2",
            "Team": "team_t2"
        })

        return df_t1, df_t2
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

def dataCredentials(gid):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    path = os.path.join("utils", "credentials.json")
    creds = ServiceAccountCredentials.from_json_keyfile_name(path, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(DOCUMENT_ID)
    worksheet = sheet.get_worksheet_by_id(int(gid))
    return worksheet

def add_register(date, name, error, team, corporation, add_hours, remove_hours, add_value, remove_value, total):
    """Add a new register to the database"""
    try:
        new_row = [
            str(date.strftime("%m/%d/%Y")),
            name,
            error,
            team,
            corporation,
            float(add_value / add_hours if add_hours > 0 else 0),  # payrate
            add_hours,
            remove_hours,
            add_value,
            remove_value,
            total
        ]
        dataCredentials(GID_T1).append_row(new_row, value_input_option="USER_ENTERED")
        st.cache_data.clear()  # Clear cache to force reload
        return True
    except Exception as e:
        logger.error(f"Error adding register: {str(e)}")
        return False

def add_user(name, payrate, corporation, team):
    """Add a new user to the database"""
    try:
        new_row = [
            name,
            corporation,
            payrate,
            team
        ]
        dataCredentials(GID_T2).append_row(new_row, value_input_option="USER_ENTERED")
        st.cache_data.clear()  # Clear cache to force reload
        return True
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        return False

def sync_and_reload():
    """Clear cache and reload data"""
    st.cache_data.clear()
    return load_data()