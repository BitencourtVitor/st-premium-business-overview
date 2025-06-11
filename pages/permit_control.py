import streamlit as st
import pandas as pd
from datetime import datetime
import logging
from database.database_permit_control import *
from utils.st_custom import *
from utils.modal_permit_control import permit_modal

logger = logging.getLogger(__name__)

def initialize_session_state():
    """Initialize session state variables for permit control"""
    if 'model_select' not in st.session_state:
        st.session_state['model_select'] = "All"
    if 'situation_select' not in st.session_state:
        st.session_state['situation_select'] = "All"
    if 'jobsites_state' not in st.session_state:
        st.session_state.jobsites_state = {}
    if 'select_all_jobsites' not in st.session_state:
        st.session_state.select_all_jobsites = True
    if 'lot_address_filter' not in st.session_state:
        st.session_state['lot_address_filter'] = ""
    if 'filtered_df' not in st.session_state:
        st.session_state['filtered_df'] = None

def apply_filters(df):
    """Apply all filters to the dataframe and update session state"""
    filtered_df = df.copy()

    # Apply model filter
    if st.session_state['model_select'] != "All":
        filtered_df = filtered_df[filtered_df["Model"] == st.session_state['model_select']]

    # Apply situation filter
    if st.session_state['situation_select'] != "All":
        filtered_df = filtered_df[filtered_df["Situation"] == st.session_state['situation_select']]

    # Apply jobsite filter
    if st.session_state['selected_jobsites']:
        filtered_df = filtered_df[filtered_df["Jobsite"].isin(st.session_state['selected_jobsites'])]

    # Apply lot/address text filter
    if st.session_state['lot_address_filter']:
        filtered_df = filtered_df[filtered_df["LOT/ADDRESS"].str.contains(
            st.session_state['lot_address_filter'], 
            case=False, 
            na=False
        )]

    # Update session state with filtered dataframe
    st.session_state['filtered_df'] = filtered_df
    return filtered_df

def calculate_permit_metrics(row):
    """Calculate metrics for a permit record"""
    metrics = {}
    
    # Convert dates to datetime if they exist
    Request_date = pd.to_datetime(row["Request Date"], errors='coerce')
    application_date = pd.to_datetime(row["Application Date"], errors='coerce')
    issue_date = pd.to_datetime(row["Issue Date"], errors='coerce')
    
    # Calculate processing time if both Request and issue dates exist
    if pd.notna(Request_date) and pd.notna(issue_date):
        processing_time = (issue_date - Request_date).days
        metrics["Processing Time"] = f"{processing_time} days"
    else:
        metrics["Processing Time"] = "N/A"
    
    # Add status indicators
    metrics["Status"] = row["Situation"]
    
    # Add dates with formatting
    metrics["Request"] = Request_date.strftime("%m/%d/%Y") if pd.notna(Request_date) else "N/A"
    metrics["Application"] = application_date.strftime("%m/%d/%Y") if pd.notna(application_date) else "N/A"
    metrics["Issue"] = issue_date.strftime("%m/%d/%Y") if pd.notna(issue_date) else "N/A"
    
    return metrics

def show_permit_card(row):
    """Display a card for a permit record"""
    metrics = calculate_permit_metrics(row)
    
    with st.container(border=True):
        # Header with Model and Jobsite
        st.markdown(f"### {row['Model']} - {row['Jobsite']}")
        
        # Main content in columns
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        
        with col1:
            st.markdown("##### Location")
            st.markdown(f"{row['LOT/ADDRESS']}")
            if pd.notna(row["Observation"]):
                st.markdown("##### Observation")
                st.markdown(f"{row['Observation']}")
        
        with col2:
            st.markdown("##### Timeline")
            st.markdown(f"**Request** {metrics['Request']}")
            st.markdown(f"**Application** {metrics['Application']}")
            st.markdown(f"**Issue** {metrics['Issue']}")
        
        with col3:
            st.markdown("##### Metrics")
            st.markdown(f"**Status** {metrics['Status']}")
            st.markdown(f"**Processing Time** {metrics['Processing Time']}")
            
        with col4:
            if pd.notna(row["Permit File"]) and row["Permit File"].strip():
                st.link_button(
                    ":material/draft: See the permit",
                    row["Permit File"],
                    use_container_width=True,
                    help="Click to open the permit PDF in a new tab"
                )
            else:
                st.markdown("*No file available*")

def show_screen(user_data):
    """Main function to display the permit control screen"""
    initialize_session_state()
    
    # Load data
    df = load_data_permit_control()
    if df.empty:
        st.error("Error loading data. Please try again later.")
        return

    # Header section with title, empty space, manage button, refresh button and filters
    col_title, col_empty, col_manage, col_refresh, col_filters1, col_filters2 = st.columns([0.23, 0.01, 0.14, 0.05, 0.29, 0.28], vertical_alignment="bottom")
    
    with col_title:
        st.write("## Permit Control")
    
    with col_empty:
        st.empty()
    
    with col_manage:
        if "permits_admin" in user_data.get("roles", []):
            if st.button(":material/draw: Manage Database", key="manage_button_permit_control", type='secondary'):
                st.session_state['show_permit_modal'] = True
                st.session_state['active_tab'] = "Add Permit"
    
    with col_refresh:
        if st.button(":material/sync:", key="permit_control_refresh_button", help="Click to refresh", type='secondary'):
            df = sync_and_reload()
    
    with col_filters1:
        # Get unique models and ensure they are strings, removing any whitespace
        models = ["All"] + sorted([str(x).strip() for x in df["Model"].dropna().unique()])
        selected_models = st.segmented_control(
            label="Model",
            options=models,
            key="model_select",
            selection_mode="multi"
        )
    
    with col_filters2:
        # Get unique situations and ensure they are strings, removing any whitespace
        situations = ["All"] + sorted([str(x).strip() for x in df["Situation"].dropna().unique()])
        selected_situations = st.segmented_control(
            label="Situation",
            options=situations,
            key="situation_select",
            selection_mode="multi"
        )

    # Lot/Address filter and date filters in columns
    col_lot, col_date_start, col_date_end = st.columns([0.55, 0.15, 0.15], gap="large")
    
    with col_lot:
        lot_address = st.text_input(
            "Filter by Lot/Address",
            key="lot_address_filter",
            placeholder="Type to filter..."
        )
    
    with col_date_start:
        min_date = pd.to_datetime(df["Request Date"], errors='coerce').min()
        start_date = st.date_input(
            "Start Date",
            value=min_date,
            min_value=min_date,
            max_value=pd.to_datetime(df["Request Date"], errors='coerce').max(),
            key="start_date_filter",
            format="MM/DD/YYYY"
        )
    
    with col_date_end:
        max_date = pd.to_datetime(df["Request Date"], errors='coerce').max()
        end_date = st.date_input(
            "End Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            key="end_date_filter",
            format="MM/DD/YYYY"
        )

    # Jobsites filter and cards container
    col_jobsites, col_cards = st.columns([0.2, 0.8])
    
    with col_jobsites:
        # Jobsites checkboxes in a bordered container
        with st.container(border=True, height=550):
            st.write("Jobsites")
            # Get unique jobsites and ensure they are strings, removing any whitespace
            jobsites = sorted([str(x).strip() for x in df["Jobsite"].dropna().unique()])
            
            # Initialize jobsites_state if needed
            if not st.session_state.jobsites_state or set(st.session_state.jobsites_state.keys()) != set(jobsites):
                st.session_state.jobsites_state = {jobsite: True for jobsite in jobsites}
            
            # Select All / Unselect All buttons
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Select all", key="select_all_jobsites_btn"):
                    for jobsite in jobsites:
                        st.session_state.jobsites_state[jobsite] = True
                        st.session_state[f"jobsite_{jobsite}"] = True
                    st.session_state.select_all_jobsites = True
            with col_btn2:
                if st.button("Unselect all", key="unselect_all_jobsites_btn"):
                    for jobsite in jobsites:
                        st.session_state.jobsites_state[jobsite] = False
                        st.session_state[f"jobsite_{jobsite}"] = False
                    st.session_state.select_all_jobsites = False
            
            for jobsite in jobsites:
                key = f"jobsite_{jobsite}"
                checked = st.checkbox(jobsite, key=key,
                    on_change=lambda j=jobsite: st.session_state.jobsites_state.update({j: st.session_state[f"jobsite_{j}"]}))
                st.session_state.jobsites_state[jobsite] = checked
            st.session_state.select_all_jobsites = all(st.session_state.jobsites_state.values())
    
    with col_cards:
        with st.container(border=True):
            # Apply filters using the widget values directly
            filtered_df = df.copy()

            # Apply model filter
            if "All" not in selected_models:
                filtered_df = filtered_df[filtered_df["Model"].astype(str).str.strip().isin(selected_models)]

            # Apply situation filter
            if "All" not in selected_situations:
                filtered_df = filtered_df[filtered_df["Situation"].astype(str).str.strip().isin(selected_situations)]

            # Apply jobsite filter
            selected_jobsites = [jobsite for jobsite, checked in st.session_state.jobsites_state.items() if checked]
            if selected_jobsites:
                filtered_df = filtered_df[filtered_df["Jobsite"].astype(str).str.strip().isin(selected_jobsites)]

            # Apply lot/address text filter
            if lot_address:
                filtered_df = filtered_df[filtered_df["LOT/ADDRESS"].astype(str).str.strip().str.contains(
                    lot_address, 
                    case=False, 
                    na=False
                )]

            # Apply date range filter
            filtered_df['Request Date'] = pd.to_datetime(filtered_df['Request Date'], errors='coerce')
            start_datetime = pd.to_datetime(start_date)
            end_datetime = pd.to_datetime(end_date)
            filtered_df = filtered_df[
                (filtered_df['Request Date'] >= start_datetime) &
                (filtered_df['Request Date'] <= end_datetime + pd.Timedelta(days=1))
            ]

            # Sort by Request date
            filtered_df = filtered_df.sort_values('Request Date')

            # Header with metrics
            col_title, col_empty, col_not_applied, col_applied, col_issued = st.columns([0.20, 0.50, 0.10, 0.10, 0.10])
            
            with col_title:
                st.write("#### Permit List")
            
            with col_empty:
                st.empty()
            
            with col_not_applied:
                not_applied_count = len(filtered_df[filtered_df["Situation"].astype(str).str.strip() == "Not Applied"])
                st.markdown(f"<p style='color: #ff4b4b; font-size: 1.5rem; font-weight: bold; text-align: center;'>{not_applied_count}</p>", unsafe_allow_html=True)
                st.markdown("<p style='color: #ff4b4b; text-align: center;'>Not Applied</p>", unsafe_allow_html=True)
            
            with col_applied:
                applied_count = len(filtered_df[filtered_df["Situation"].astype(str).str.strip() == "Applied"])
                st.markdown(f"<p style='color: orange; font-size: 1.5rem; font-weight: bold; text-align: center;'>{applied_count}</p>", unsafe_allow_html=True)
                st.markdown("<p style='color: orange; text-align: center;'>Applied</p>", unsafe_allow_html=True)
            
            with col_issued:
                issued_count = len(filtered_df[filtered_df["Situation"].astype(str).str.strip() == "Issued"])
                st.markdown(f"<p style='color: green; font-size: 1.5rem; font-weight: bold; text-align: center;'>{issued_count}</p>", unsafe_allow_html=True)
                st.markdown("<p style='color: green; text-align: center;'>Issued</p>", unsafe_allow_html=True)

            # Cards container
            with st.container(border=False, height=429):
                # Not Applied
                not_applied_df = filtered_df[filtered_df["Situation"].astype(str).str.strip() == "Not Applied"]
                if not not_applied_df.empty:
                    st.badge("Not Applied", icon=":material/priority_high:", color="red")
                    for _, row in not_applied_df.iterrows():
                        show_permit_card(row)
                
                # Applied
                applied_df = filtered_df[filtered_df["Situation"].astype(str).str.strip() == "Applied"]
                if not applied_df.empty:
                    st.badge("Applied", icon=":material/more_horiz:", color="orange")
                    for _, row in applied_df.iterrows():
                        show_permit_card(row)
                
                # Issued
                issued_df = filtered_df[filtered_df["Situation"].astype(str).str.strip() == "Issued"]
                if not issued_df.empty:
                    st.badge("Issued", icon=":material/check:", color="green")
                    for _, row in issued_df.iterrows():
                        show_permit_card(row)

    # Show modal if needed
    if st.session_state.get('show_permit_modal', False):
        permit_modal()
