import pandas as pd
import streamlit as st
import logging

logger = logging.getLogger(__name__)

@st.cache_data(ttl=600)
def load_data_accounting_indicators():
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

def sync_and_reload():
    st.cache_data.clear()
    return load_data_accounting_indicators()

def head_accounting_indicators_public():
    """Retorna o head do DataFrame público para depuração."""
    df = load_data_accounting_indicators()
    return df.head() 