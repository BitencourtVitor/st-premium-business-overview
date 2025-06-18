import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DOCUMENT_ID = "1Em_Wyj8EiBeo56zGrShKEP9yFCMDVmkR-_EoiNXI3YA"
GID = "1016235500"

def get_url(gid):
    return f"https://docs.google.com/spreadsheets/d/{DOCUMENT_ID}/export?format=xlsx&gid={gid}"

@st.cache_data(ttl=600)
def load_data_permit_control():
    try:
        df = pd.read_excel(get_url(GID), engine="openpyxl")

        df = df.rename(columns={
            "MODEL": "Model",
            "JOBSITE": "Jobsite",
            "LOT/ADDRESS": "LOT/ADDRESS",
            "SITUAÇÃO": "Situation",
            "SOLICITAÇÃO": "Request Date",
            "APLICAÇÃO": "Application Date",
            "EMISSÃO": "Issue Date",
            "OBSERVAÇÃO": "Observation",
            "ARQUIVO": "Permit File"
        })
        return df
    
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

def dataCredentials(gid):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    path = os.path.join("antique", "credentials.json")
    creds = ServiceAccountCredentials.from_json_keyfile_name(path, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(DOCUMENT_ID)
    worksheet = sheet.get_worksheet_by_id(int(gid))
    return worksheet

def add_register_permit_control(model, jobsite, lot_address, situation, request_date, application_date, issue_date, observation, permit_file):
    """Add a new permit to the database"""
    try:
        worksheet = dataCredentials(GID)
        worksheet.append_row([
            model,
            jobsite,
            lot_address,
            situation,
            str(request_date.strftime("%m/%d/%Y")) if request_date else "",
            str(application_date.strftime("%m/%d/%Y")) if application_date else "",
            str(issue_date.strftime("%m/%d/%Y")) if issue_date else "",
            observation,
            permit_file
        ])
        st.cache_data.clear()  # Clear cache to force reload
        return True
    except Exception as e:
        logger.error(f"Error adding permit: {str(e)}")
        return False

def sync_and_reload():
    """Clear cache and reload data"""
    st.cache_data.clear()
    return load_data_permit_control()

def update_permit_control(row_id, model, jobsite, lot_address, situation, request_date, application_date, issue_date, observation, permit_file):
    """Update an existing permit in the database"""
    try:
        worksheet = dataCredentials(GID)
        # Get all data to find the correct row
        all_data = worksheet.get_all_records()
        if row_id < len(all_data):
            # Update the row (row_id + 2 because sheet is 1-indexed and has header)
            row_num = row_id + 2
            worksheet.update(f'A{row_num}:I{row_num}', [[
                model,
                jobsite,
                lot_address,
                situation,
                str(request_date.strftime("%m/%d/%Y")) if request_date else "",
                str(application_date.strftime("%m/%d/%Y")) if application_date else "",
                str(issue_date.strftime("%m/%d/%Y")) if issue_date else "",
                observation,
                permit_file
            ]])
            st.cache_data.clear()  # Clear cache to force reload
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating permit: {str(e)}")
        return False

def delete_permit(row_data):
    """Delete a permit from the database"""
    try:
        worksheet = dataCredentials(GID)
        # Find the row that matches all the data
        all_data = worksheet.get_all_records()
        
        # Convert dates in row_data to strings for comparison
        request_date_str = pd.to_datetime(row_data["Request Date"]).strftime("%m/%d/%Y") if pd.notna(row_data["Request Date"]) else ""
        application_date_str = pd.to_datetime(row_data["Application Date"]).strftime("%m/%d/%Y") if pd.notna(row_data["Application Date"]) else ""
        issue_date_str = pd.to_datetime(row_data["Issue Date"]).strftime("%m/%d/%Y") if pd.notna(row_data["Issue Date"]) else ""
        
        for idx, row in enumerate(all_data, start=2):  # start=2 because sheet is 1-indexed and has header
            # Compare dates as strings
            if (row["MODEL"] == row_data["Model"] and
                row["JOBSITE"] == row_data["Jobsite"] and
                row["LOT/ADDRESS"] == row_data["LOT/ADDRESS"] and
                row["SITUAÇÃO"] == row_data["Situation"] and
                row["SOLICITAÇÃO"] == request_date_str and
                (not application_date_str or row["APLICAÇÃO"] == application_date_str) and
                (not issue_date_str or row["EMISSÃO"] == issue_date_str)):
                # Delete the row using delete_rows (start index, end index)
                worksheet.delete_rows(idx, idx)
                st.cache_data.clear()  # Clear cache to force reload
                return True
        return False
    except Exception as e:
        logger.error(f"Error deleting permit: {str(e)}")
        return False