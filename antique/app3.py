import streamlit as st
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pickle
import pandas as pd
from googleapiclient.http import MediaIoBaseDownload
import io

st.set_page_config(page_title="Profit and Loss", page_icon=":money_with_wings:", layout="wide", initial_sidebar_state="expanded")

PL_archives = {
    'profit_and_loss_2023' : "1V8-QAgIeXG04SOq9PTinqlkR_C1je05A",
    'profit_and_loss_2024' : "1cFybVpEU6ivJU5EV_bPJRqz0o_Q6cLHP",
    'profit_and_loss_2025' : "15NeTamknGAYze-T45aProfvS7ithWNWl"
}


def get_google_drive_service():
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    # Use service account credentials
    credentials_path = os.path.join('antique', 'credentials2.json')
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES)

    return build('drive', 'v3', credentials=credentials)

def list_files_in_folder(folder_id):
    try:
        service = get_google_drive_service()
        
        # Query to get files in the specified folder
        query = f"'{folder_id}' in parents and trashed = false"
        
        # Get the list of files
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print('No files found in the specified folder.')
            return
        
        print('\nFiles in folder:')
        print('-' * 80)
        for item in items:
            print(f"Name: {item['name']}")
            print(f"ID: {item['id']}")
            print(f"Type: {item['mimeType']}")
            print(f"Created: {item['createdTime']}")
            print(f"Modified: {item['modifiedTime']}")
            print('-' * 80)
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def download_file(service, file_id):
    """Download a file from Google Drive given its ID."""
    try:
        request = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        file.seek(0)
        return file
    except Exception as e:
        print(f"An error occurred while downloading the file: {str(e)}")
        return None

def CollectProfitAndLoss(year='2023'):
    """
    Collects the Profit and Loss data for a specific year.
    Args:
        year (str): The year to collect data for (default: '2023')
    Returns:
        pandas.DataFrame: DataFrame containing the Profit and Loss data
    """
    try:
        service = get_google_drive_service()
        
        # Get the folder ID for the specified year
        folder_id = PL_archives.get(f'profit_and_loss_{year}')
        if not folder_id:
            raise Exception(f"No folder ID found for year {year}")
        
        # Query to find all PL files in the specified year's folder
        query = f"name contains 'PL_' and '{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            pageSize=100,  # Increased to get all files
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            raise Exception(f"No PL files found for {year} in the specified folder")
        
        all_dfs = []
        for file in files:
            file_id = file['id']
            downloaded_file = download_file(service, file_id)
            
            if downloaded_file is None:
                print(f"Failed to download file: {file['name']}")
                continue
            
            # Extract month from filename (e.g., "PL_01-23" -> "01")
            try:
                month = file['name'].split('_')[1].split('-')[0]
                df = pd.read_excel(downloaded_file, skiprows=3)
                df['Year'] = year
                df['Month'] = month
                all_dfs.append(df)
            except (IndexError, ValueError) as e:
                print(f"Could not extract month from filename {file['name']}: {str(e)}")
                continue
        
        if not all_dfs:
            raise Exception(f"No valid data found for {year}")
            
        # Combine all DataFrames for this year
        combined_df = pd.concat(all_dfs, ignore_index=True)
        return combined_df
        
    except Exception as e:
        print(f"Error in CollectProfitAndLoss: {str(e)}")
        return None

def TratarPL(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process and clean up the Profit and Loss DataFrame.
    
    Args:
        df (pd.DataFrame): Raw Profit and Loss DataFrame
        
    Returns:
        pd.DataFrame: Processed DataFrame with clean categories and real values
    """
    # Create a copy to avoid SettingWithCopyWarning
    df = df.copy()
    
    # Rename first column to Detail
    df.rename(columns={df.columns[0]: 'Detail'}, inplace=True)
    
    # Create and filter categories
    df['Category'] = df['Detail'].where(df['Total'].isnull())
    valid_categories = ["Cost of Goods Sold", "Expenses", "Income"]
    df = df[df['Category'].isnull() | df['Category'].isin(valid_categories)]
    df['Category'] = df['Category'].ffill()  # Using ffill() instead of fillna(method='ffill')
    
    # Filter rows with valid totals
    df = df[df['Total'].notnull()]
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
    
    # Remove summary rows
    summary_rows = [
        "Net Income", "Net Operating Income", "Net Other Income",
        "Total Contractors", "Total Cost of Goods Sold", "Total Expenses",
        "Total Income", "Total Insurance", "Total Job Supplies",
        "Total Labor", "Total Other Expenses", "Total Panels Premium",
        "Total Taxes & Licenses", "Total Vehicles Expenses", "Gross Profit"
    ]
    df = df[~df['Detail'].isin(summary_rows)]
    
    # Calculate real values (negative for costs and expenses)
    df['Total Real'] = df.apply(
        lambda row: -row['Total'] if row['Category'] in ["Cost of Goods Sold", "Expenses"] 
        else row['Total'], 
        axis=1
    )
    
    # Create Period using Month and Year from the filename
    df['Period'] = pd.to_datetime(df['Year'] + '-' + df['Month'] + '-01').dt.date
    
    # Select and return final columns
    return df[['Period', 'Category', 'Detail', 'Total Real']]

def load_all_pl_data():
    """
    Loads and processes all Profit and Loss data from 2023 to 2025.
    Returns a single DataFrame with all processed data.
    
    Returns:
        pandas.DataFrame: Combined DataFrame containing all PL data
    """
    all_years_data = []
    
    for year in ['2023', '2024', '2025']:
        df = CollectProfitAndLoss(year)
        if df is not None:
            processed_df = TratarPL(df)
            all_years_data.append(processed_df)
            st.write(f"Successfully processed {year} data")
        else:
            st.error(f"Could not load data for {year}")
    
    if all_years_data:
        # Combine all years' data
        final_df = pd.concat(all_years_data, ignore_index=True)
        return final_df
    else:
        st.error("No data was processed successfully")
        return None

if __name__ == "__main__":
    pl_data = load_all_pl_data()
    if pl_data is not None:
        st.dataframe(pl_data)