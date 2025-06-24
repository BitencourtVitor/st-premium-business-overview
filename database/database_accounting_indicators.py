import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import logging
import tempfile

logger = logging.getLogger(__name__)

DOCUMENT_ID = "1lk5ENgYagn9cBhvOtLVSJ6lVZdblrt3KteSMbqE_GSQ"
GID = 0  # Default first sheet as int

def get_url_csv(gid):
    return f"https://docs.google.com/spreadsheets/d/{DOCUMENT_ID}/export?format=csv&gid={gid}"

@st.cache_data(ttl=600)
def load_data_accounting_indicators():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        path = os.path.join("antique", "credentials.json")
        creds = ServiceAccountCredentials.from_json_keyfile_name(path, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(DOCUMENT_ID)
        worksheet = sheet.get_worksheet_by_id(GID)
        data = worksheet.get_all_values()
        if not data:
            return pd.DataFrame()
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        df = df.rename(columns={
            "Inv Date": "Inv Date",
            "Transaction type": "Transaction type",
            "INV Num": "INV Num",
            "Customer full name": "Customer full name",
            "Due date": "Due date",
            "INV Amount": "INV Amount",
            "Open balance": "Open balance",
            "EPO Number": "EPO Number",
            "Category": "Category",
            "Aging days": "Aging days",
            "Aging Intervals": "Aging Intervals",
            "Date": "Date"
        })
        return df
    except Exception as e:
        logger.error(f"Error loading accounting indicators data: {str(e)}")
        return pd.DataFrame()

def dataCredentials(gid):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    path = os.path.join("antique", "credentials.json")
    creds = ServiceAccountCredentials.from_json_keyfile_name(path, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(DOCUMENT_ID)
    worksheet = sheet.get_worksheet_by_id(int(gid))
    return worksheet

def sync_and_reload():
    st.cache_data.clear()
    return load_data_accounting_indicators()

def load_data_accounting_indicators_public():
    """Carrega os dados da planilha Google como CSV público, sem autenticação."""
    try:
        url = "https://docs.google.com/spreadsheets/d/1lk5ENgYagn9cBhvOtLVSJ6lVZdblrt3KteSMbqE_GSQ/export?format=csv"
        df = pd.read_csv(url)
        df = df.rename(columns={
            "Inv Date": "Inv Date",
            "Transaction type": "Transaction type",
            "INV Num": "INV Num",
            "Customer full name": "Customer full name",
            "Due date": "Due date",
            "INV Amount": "INV Amount",
            "Open balance": "Open balance",
            "EPO Number": "EPO Number",
            "Category": "Category",
            "Aging days": "Aging days",
            "Aging Intervals": "Aging Intervals",
            "Date": "Date"
        })
        return df
    except Exception as e:
        logger.error(f"Error loading public accounting indicators data: {str(e)}")
        return pd.DataFrame()

def head_accounting_indicators_public():
    """Retorna o head do DataFrame público para depuração."""
    df = load_data_accounting_indicators_public()
    return df.head() 