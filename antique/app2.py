import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

database_framing = "13Q4V2_PHWijrIYj5Ap9M-KWsuNj2mIW1"
days_sales = "142039135"
days_payable = "1361790735"
aging_receivables = "542587624"
aging_payables = "1753316251"

def get_sales(days_sales):
    return f"https://docs.google.com/spreadsheets/d/{database_framing}/export?format=xlsx&gid={days_sales}"

def get_payable(days_payable):
    return f"https://docs.google.com/spreadsheets/d/{database_framing}/export?format=xlsx&gid={days_payable}"

def get_aging_receivables(aging_receivables):
    return f"https://docs.google.com/spreadsheets/d/{database_framing}/export?format=xlsx&gid={aging_receivables}"

def get_aging_payables(aging_payables):
    return f"https://docs.google.com/spreadsheets/d/{database_framing}/export?format=xlsx&gid={aging_payables}"

# @st.cache_data(ttl=600)
def load_sales_data():
    try:
        df_sales = pd.read_excel(get_sales(days_sales), engine="openpyxl", header=3)
        df_sales = df_sales.drop(df_sales.index[0])

        df_sales['Date'] = pd.to_datetime(df_sales['Date'], errors='coerce')
        df_sales['Due date'] = pd.to_datetime(df_sales['Due date'], errors='coerce')
        df_sales['Paid date'] = pd.to_datetime(df_sales['Paid date'], errors='coerce')

        df_sales = df_sales.drop(columns=['Num'])
        df_sales = df_sales.drop(columns=['Payment status'])
        df_sales['Amount'] = pd.to_numeric(df_sales['Amount'], errors='coerce')

        df_sales = df_sales[df_sales['Paid date'].notna()]

        df_sales['Days Taken'] = (df_sales['Paid date'] - df_sales['Date']).dt.days

        df_sales['Date'] = df_sales['Date'].dt.strftime('%m/%d/%Y')
        df_sales['Due date'] = df_sales['Due date'].dt.strftime('%m/%d/%Y')
        df_sales['Paid date'] = df_sales['Paid date'].dt.strftime('%m/%d/%Y')

        df_sales = df_sales.rename(columns={'Paid date': 'Paid Date'})
        df_sales = df_sales.rename(columns={'Due date': 'Due Date'})

        df_sales['Amount'] = df_sales['Amount'].astype(float)

        df_sales = df_sales[['Date', 'Due Date', 'Paid Date', 'Days Taken', 'Customer', 'Amount']]

        return df_sales
    except Exception as e:
        st.error(f"Error loading sales data: {str(e)}")
        return pd.DataFrame()

# @st.cache_data(ttl=600)
def load_payable_data():
    try:

        df_payable = pd.read_excel(get_payable(days_payable), engine="openpyxl", skiprows=3)

        df_payable = df_payable.drop(columns=["Billable", "Quantity", "Customer", "Product/Service", "Transaction Details po Amount", "Transaction Details po Rate", "Transaction Details po Transaction Type", "Transaction Details po Transaction Id", "Transaction Details po Qty", "Transaction Details po Status", "Line Order", "Net amount line", "Rate", "Created date line", "Last modified date line", "Coluna1", "Coluna2", "Ledger amount"])
        
        df_payable['Amount line'] = pd.to_numeric(df_payable['Amount line'], errors='coerce')

        df_payable['Date'] = pd.to_datetime(df_payable['Date'], errors='coerce')
        df_payable['Paid date'] = pd.to_datetime(df_payable['Paid date'], errors='coerce')
        
        df_payable = df_payable[
            (df_payable['Split account'] != 'Accounts Payable (A/P)') &
            (df_payable['Amount line'].fillna(0) != 0) &
            (df_payable['Paid date'].notna())
        ]

        df_payable['Days Taken'] = (df_payable['Paid date'] - df_payable['Date']).dt.days

        df_payable['Date'] = df_payable['Date'].dt.strftime('%m/%d/%Y')
        df_payable['Paid date'] = df_payable['Paid date'].dt.strftime('%m/%d/%Y')

        df_payable = df_payable.rename(columns={'Paid date': 'Paid Date'})
        df_payable = df_payable.rename(columns={'Amount line': 'Amount'})
        df_payable = df_payable.rename(columns={'Vendor name': 'Vendor'})
        df_payable = df_payable.rename(columns={'Split account': 'Split Account'})

        df_payable = df_payable[['Date', 'Paid Date', 'Days Taken', 'Vendor', 'Split Account', 'Amount']]

        return df_payable
    except Exception as e:
        st.error(f"Error loading payable data: {str(e)}")
        return pd.DataFrame()

# df_sales = load_sales_data()
# df_payable = load_payable_data()
# st.dataframe(df_sales, use_container_width=True)
# st.dataframe(df_payable, use_container_width=True)

def load_aging_receivables_data():
    try:

        df_aging_receivables = pd.read_excel(get_aging_receivables(aging_receivables), engine="openpyxl", skiprows=3)

        df_aging_receivables = df_aging_receivables.drop(columns=["Phone", "Shipping Address", "company Name", "Client/Vendor Message", "Memo/Description", "Create Date", "Created By", "Last Modified", "Last Modified By"])

        df_aging_receivables = df_aging_receivables.drop(columns=["Store", "Phone Numbers"])

        df_aging_receivables = df_aging_receivables.dropna(subset=['Transaction Type'])

        df_aging_receivables['Customer'] = df_aging_receivables['Customer'].str.title()
        df_aging_receivables['Delivery Address'] = df_aging_receivables['Delivery Address'].str.lower()

        df_aging_receivables = df_aging_receivables[df_aging_receivables['Amount'] > 0]

        temporary_aging_columns = df_aging_receivables['Customer'].str.split(':', n=1, expand=True)

        df_aging_receivables['Customer.1'] = temporary_aging_columns[0]
        df_aging_receivables['Customer.2'] = temporary_aging_columns[1]

        df_aging_receivables = df_aging_receivables.drop(columns=['Customer'])

        df_aging_receivables = df_aging_receivables.rename(columns={'Customer.1': 'Customer', 'Customer.2': 'Description'})

        df_aging_receivables['Amount'] = pd.to_numeric(df_aging_receivables['Amount'], errors='coerce')
        df_aging_receivables['Open Balance'] = pd.to_numeric(df_aging_receivables['Open Balance'], errors='coerce')
        df_aging_receivables['Past Due'] = pd.to_numeric(df_aging_receivables['Past Due'], errors='coerce').astype('Int64')

        df_aging_receivables['Sent'] = df_aging_receivables['Sent'].apply(lambda x: 'Yes' if x == 'Sent' else 'No')

        df_aging_receivables['Billing Address'] = df_aging_receivables['Billing Address'].fillna('(No Billing Address)')

        df_aging_receivables['Date'] = pd.to_datetime(df_aging_receivables['Date'], errors='coerce')
        df_aging_receivables['Due Date'] = pd.to_datetime(df_aging_receivables['Due Date'], errors='coerce')

        df_aging_receivables = df_aging_receivables[df_aging_receivables['Date'] >= '2023-01-01']
        
        df_aging_receivables['Date'] = df_aging_receivables['Date'].dt.strftime('%m/%d/%Y')
        df_aging_receivables['Due Date'] = df_aging_receivables['Due Date'].dt.strftime('%m/%d/%Y')
        
        def get_segment(past_due):
            match past_due:
                case x if x <= 0:
                    return 'Current'
                case x if 1 <= x <= 30:
                    return '1-30'
                case x if 31 <= x <= 60:
                    return '31-60'
                case x if 61 <= x <= 90:
                    return '61-90'
                case x if 91 <= x <= 120:
                    return '91-120'
                case x if x >= 121:
                    return '121+'

        df_aging_receivables['Segment'] = df_aging_receivables['Past Due'].apply(get_segment)

        df_aging_receivables = df_aging_receivables[['Date', 'Due Date', 'Past Due', 'Segment','Transaction Type', 'Num', 'Customer', 'Description', 'Email', 'Terms', 'Billing Address', 'Amount', 'Sent']]

        return df_aging_receivables
    except Exception as e:
        st.error(f"Error loading aging receivables data: {str(e)}")
        return pd.DataFrame()
    
def load_aging_payables_data():
    try:
        df_aging_payables = pd.read_excel(get_aging_payables(aging_payables), engine="openpyxl", skiprows=3)

        if df_aging_payables.empty:
            st.error("No data found in the aging payables file")
            return pd.DataFrame()

        if df_aging_payables.iloc[0].isna().all():
            df_aging_payables = df_aging_payables.drop(df_aging_payables.index[0])

        df_aging_payables['Amount'] = pd.to_numeric(df_aging_payables['Amount'], errors='coerce')
        df_aging_payables['Open Balance'] = pd.to_numeric(df_aging_payables['Open Balance'], errors='coerce')
        df_aging_payables['Past Due'] = pd.to_numeric(df_aging_payables['Past Due'], errors='coerce').astype('Int64')

        df_aging_payables['Date'] = pd.to_datetime(df_aging_payables['Date'], errors='coerce')
        df_aging_payables['Due Date'] = pd.to_datetime(df_aging_payables['Due Date'], errors='coerce')
        df_aging_payables = df_aging_payables[df_aging_payables['Date'] >= '2023-01-01']
        df_aging_payables['Date'] = df_aging_payables['Date'].dt.strftime('%m/%d/%Y')
        df_aging_payables['Due Date'] = df_aging_payables['Due Date'].dt.strftime('%m/%d/%Y')

        def get_segment(past_due):
            match past_due:
                case x if x <= 0:
                    return 'Current'
                case x if 1 <= x <= 30:
                    return '1-30'
                case x if 31 <= x <= 60:
                    return '31-60'
                case x if 61 <= x <= 90:
                    return '61-90'
                case x if 91 <= x <= 120:
                    return '91-120'
                case x if x >= 121:
                    return '121+'

        df_aging_payables['Segment'] = df_aging_payables['Past Due'].apply(get_segment)
        df_aging_payables = df_aging_payables[['Date', 'Due Date', 'Past Due', 'Segment', 'Transaction Type', 'Num', 'Vendor', 'Terms', 'Amount']]

        return df_aging_payables
    except Exception as e:
        st.error(f"Error in load_aging_payables_data: {str(e)}")
        return pd.DataFrame()
    
# df_aging_receivables = load_aging_receivables_data()
# df_aging_payables = load_aging_payables_data()
# st.dataframe(df_aging_receivables, use_container_width=True)
# st.dataframe(df_aging_payables, use_container_width=True)