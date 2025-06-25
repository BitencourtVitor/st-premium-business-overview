import streamlit as st
import pandas as pd
from datetime import datetime
from database.database_permit_control import load_data_permit_control, add_register_permit_control, update_permit_control, delete_permit, dataCredentials, GID
import logging

logger = logging.getLogger(__name__)

def initialize_modal_session_state():
    """Initialize session state variables for permit modal"""
    # Add tab state
    if "permit_date" not in st.session_state:
        st.session_state.permit_date = datetime.today()
    if "permit_model" not in st.session_state:
        st.session_state.permit_model = None
    if "permit_jobsite" not in st.session_state:
        st.session_state.permit_jobsite = None
    if "permit_lot_address" not in st.session_state:
        st.session_state.permit_lot_address = ""
    if "permit_situation" not in st.session_state:
        st.session_state.permit_situation = None
    if "permit_application_date" not in st.session_state:
        st.session_state.permit_application_date = None
    if "permit_issue_date" not in st.session_state:
        st.session_state.permit_issue_date = None
    if "permit_observation" not in st.session_state:
        st.session_state.permit_observation = ""
    if "permit_file" not in st.session_state:
        st.session_state.permit_file = ""
    
    # Edit tab state
    if "edit_lot_address" not in st.session_state:
        st.session_state.edit_lot_address = None
    if "edit_permit_date" not in st.session_state:
        st.session_state.edit_permit_date = None
    if "edit_permit_model" not in st.session_state:
        st.session_state.edit_permit_model = None
    if "edit_permit_jobsite" not in st.session_state:
        st.session_state.edit_permit_jobsite = None
    if "edit_permit_situation" not in st.session_state:
        st.session_state.edit_permit_situation = None
    if "edit_permit_application_date" not in st.session_state:
        st.session_state.edit_permit_application_date = None
    if "edit_permit_issue_date" not in st.session_state:
        st.session_state.edit_permit_issue_date = None
    if "edit_permit_observation" not in st.session_state:
        st.session_state.edit_permit_observation = None
    if "edit_permit_file" not in st.session_state:
        st.session_state.edit_permit_file = ""
    
    # Delete tab state
    if "delete_lot_address" not in st.session_state:
        st.session_state.delete_lot_address = None

def reset_add_tab_state():
    """Reset add tab state"""
    st.session_state.permit_date = datetime.today()
    st.session_state.permit_model = None
    st.session_state.permit_jobsite = None
    st.session_state.permit_lot_address = ""
    st.session_state.permit_situation = None
    st.session_state.permit_application_date = None
    st.session_state.permit_issue_date = None
    st.session_state.permit_observation = ""
    st.session_state.permit_file = ""

def reset_edit_tab_state():
    """Reset edit tab state"""
    st.session_state.edit_lot_address = None
    st.session_state.edit_permit_date = None
    st.session_state.edit_permit_model = None
    st.session_state.edit_permit_jobsite = None
    st.session_state.edit_permit_situation = None
    st.session_state.edit_permit_application_date = None
    st.session_state.edit_permit_issue_date = None
    st.session_state.edit_permit_observation = None
    st.session_state.edit_permit_file = None

def validate_dates(request_date, application_date, issue_date, situation):
    """Validate date logic based on situation"""
    if situation == "Not Applied":
        if application_date is not None or issue_date is not None:
            return False, "Not Applied permits cannot have Application or Issue dates"
        return True, None
    
    if situation == "Applied":
        if issue_date is not None:
            return False, "Applied permits cannot have an Issue date"
        if application_date is None:
            return False, "Applied permits must have an Application date"
        if application_date < request_date:
            return False, "Application date must be after Request date"
        return True, None
    
    if situation == "Issued":
        if application_date is None or issue_date is None:
            return False, "Issued permits must have both Application and Issue dates"
        if application_date < request_date:
            return False, "Application date must be after Request date"
        if issue_date < application_date:
            return False, "Issue date must be after Application date"
        return True, None
    
    return False, "Invalid situation"

def load_permit_data_for_edit(lot_address):
    """Load permit data into session state for editing"""
    df = load_data_permit_control()
    row = df[df["LOT/ADDRESS"] == lot_address].iloc[0]
    
    st.session_state.edit_permit_date = pd.to_datetime(row["Request Date"])
    st.session_state.edit_permit_model = row["Model"]
    st.session_state.edit_permit_jobsite = row["Jobsite"]
    st.session_state.edit_permit_situation = row["Situation"]
    st.session_state.edit_permit_application_date = pd.to_datetime(row["Application Date"]) if pd.notna(row["Application Date"]) else None
    st.session_state.edit_permit_issue_date = pd.to_datetime(row["Issue Date"]) if pd.notna(row["Issue Date"]) else None
    st.session_state.edit_permit_observation = row["Observation"] if pd.notna(row["Observation"]) else ""
    st.session_state.edit_permit_file = row["Permit File"] if pd.notna(row["Permit File"]) else ""

def save_new_permit():
    """Save a new permit"""
    try:
        # Get values from session state
        request_date = st.session_state.get("permit_date", datetime.today())
        model = st.session_state.get("permit_model", "")
        jobsite = st.session_state.get("permit_jobsite", "")
        lot_address = st.session_state.get("permit_lot_address", "")
        situation = st.session_state.get("permit_situation", "")
        application_date = st.session_state.get("permit_application_date", None)
        issue_date = st.session_state.get("permit_issue_date", None)
        observation = st.session_state.get("permit_observation", "")
        permit_file = st.session_state.get("permit_file", "")

        # Validate required fields
        if not model or not jobsite or not lot_address or not situation:
            st.error("Please fill in all required fields")
            return

        # Validate dates based on situation
        is_valid, error_msg = validate_dates(request_date, application_date, issue_date, situation)
        if not is_valid:
            st.error(error_msg)
            return

        # Add new permit
        success = add_register_permit_control(
            model,
            jobsite,
            lot_address,
            situation,
            request_date,
            application_date,
            issue_date,
            observation,
            permit_file
        )

        if success:
            # Clear form and close modal
            reset_add_tab_state()
            st.session_state['show_permit_modal'] = False
        else:
            st.error("Failed to add permit")

    except Exception as e:
        st.error(f"Error saving permit: {str(e)}")

def save_edited_permit():
    """Save the edited permit"""
    try:
        if not st.session_state.edit_lot_address:
            st.error("Please select a permit to edit")
            return

        # Get values from session state
        request_date = st.session_state.get("edit_permit_date")
        model = st.session_state.get("edit_permit_model")
        jobsite = st.session_state.get("edit_permit_jobsite")
        lot_address = st.session_state.get("edit_lot_address")
        situation = st.session_state.get("edit_permit_situation")
        application_date = st.session_state.get("edit_permit_application_date")
        issue_date = st.session_state.get("edit_permit_issue_date")
        observation = st.session_state.get("edit_permit_observation")
        permit_file = st.session_state.get("edit_permit_file")

        # Validate required fields
        if not model or not jobsite or not lot_address or not situation:
            st.error("Please fill in all required fields")
            return

        # Validate dates based on situation
        is_valid, error_msg = validate_dates(request_date, application_date, issue_date, situation)
        if not is_valid:
            st.error(error_msg)
            return

        # Find the row index for the permit
        df = load_data_permit_control()
        row_idx = df[df["LOT/ADDRESS"] == lot_address].index[0]

        # Update existing permit
        success = update_permit_control(
            row_idx,
            model,
            jobsite,
            lot_address,
            situation,
            request_date,
            application_date,
            issue_date,
            observation,
            permit_file
        )

        if success:
            # Clear form and close modal
            reset_edit_tab_state()
            st.session_state['show_permit_modal'] = False
        else:
            st.error("Failed to update permit")

    except Exception as e:
        st.error(f"Error saving permit: {str(e)}")

def delete_selected_permit():
    """Delete the selected permit"""
    try:
        if not st.session_state.delete_lot_address:
            st.error("Please select a permit to delete")
            return

        # Find the row data for the permit
        df = load_data_permit_control()
        row_data = df[df["LOT/ADDRESS"] == st.session_state.delete_lot_address].iloc[0]
        
        if delete_permit(row_data):
            st.session_state.delete_lot_address = None
            st.session_state['show_permit_modal'] = False
        else:
            st.error("Failed to delete permit")

    except Exception as e:
        st.error(f"Error deleting permit: {str(e)}")

@st.dialog("Permit Management", width="large")
def permit_modal():
    """Modal for managing permits with tabs for add, edit, and delete operations"""
    initialize_modal_session_state()
    df = load_data_permit_control()
    
    tab1, tab2, tab3 = st.tabs(["Add Permit", "Edit Permit", "Delete Permit"])
    
    with tab1:
        st.write("Fill in the permit details below.")
        
        with st.container(border=False):
            st.subheader("Permit Information")
            
            col1, col2 = st.columns([0.6, 0.4])
            
            with col1:
                st.date_input(
                    "Request Date",
                    format="MM/DD/YYYY",
                    key="permit_date"
                )
                
                permit_model = st.selectbox(
                    "Model",
                    options=sorted(df["Model"].dropna().unique()),
                    index=None,
                    key="permit_model",
                    placeholder="Select model",
                    accept_new_options=True
                )
                
                permit_jobsite = st.selectbox(
                    "Jobsite",
                    options=sorted(df["Jobsite"].dropna().unique()),
                    index=None,
                    key="permit_jobsite",
                    placeholder="Select jobsite",
                    accept_new_options=True
                )
                
                st.text_area(
                    "Lot/Address",
                    key="permit_lot_address",
                    placeholder="Enter lot/address"
                )
                            
            with col2:
                permit_situation = st.selectbox(
                    "Situation",
                    options=["Not Applied", "Applied", "Issued"],
                    index=None,
                    key="permit_situation",
                    placeholder="Select situation"
                )
                
                # Disable application date if situation is Not Applied
                application_date_disabled = permit_situation == "Not Applied"
                st.date_input(
                    "Application Date",
                    format="MM/DD/YYYY",
                    key="permit_application_date",
                    disabled=application_date_disabled
                )
                
                # Disable issue date if situation is Not Applied or Applied
                issue_date_disabled = permit_situation in ["Not Applied", "Applied"]
                st.date_input(
                    "Issue Date",
                    format="MM/DD/YYYY",
                    key="permit_issue_date",
                    disabled=issue_date_disabled
                )
                
                st.text_area(
                    "Observation",
                    key="permit_observation",
                    placeholder="Enter any additional notes"
                )
            
            st.text_area(
                "Permit File URL",
                key="permit_file",
                placeholder="Enter SharePoint PDF URL",
                help="Enter the full URL to the permit PDF file in SharePoint"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.button(
                    "Cancel",
                    key="cancel_add",
                    on_click=lambda: setattr(st.session_state, 'show_permit_modal', False)
                )
            with col2:
                st.button(
                    "Add Permit",
                    key="save_add",
                    type="primary",
                    on_click=save_new_permit
                )
    
    with tab2:
        st.write("Select a permit to edit.")
        
        # Lot/Address selector
        lot_addresses = sorted(df["LOT/ADDRESS"].dropna().unique())
        selected_lot = st.selectbox(
            "Select Lot/Address",
            options=lot_addresses,
            index=None,
            key="edit_lot_address",
            placeholder="Select a permit to edit",
            on_change=lambda: load_permit_data_for_edit(st.session_state.edit_lot_address) if st.session_state.edit_lot_address else None
        )
        
        if selected_lot:
            with st.container(border=False):
                st.subheader("Edit Permit Information")
                
                col1, col2 = st.columns([0.6, 0.4])
                
                with col1:
                    st.date_input(
                        "Request Date",
                        format="MM/DD/YYYY",
                        key="edit_permit_date"
                    )
                    
                    st.selectbox(
                        "Model",
                        options=sorted(df["Model"].dropna().unique()),
                        index=None,
                        key="edit_permit_model",
                        placeholder="Select model",
                        accept_new_options=True
                    )
                    
                    st.selectbox(
                        "Jobsite",
                        options=sorted(df["Jobsite"].dropna().unique()),
                        index=None,
                        key="edit_permit_jobsite",
                        placeholder="Select jobsite",
                        accept_new_options=True
                    )
                    
                    st.text_area(
                        "Permit File URL",
                        key="edit_permit_file",
                        placeholder="Enter SharePoint PDF URL",
                        help="Enter the full URL to the permit PDF file in SharePoint"
                    )
                
                with col2:
                    permit_situation = st.selectbox(
                        "Situation",
                        options=["Not Applied", "Applied", "Issued"],
                        index=None,
                        key="edit_permit_situation",
                        placeholder="Select situation"
                    )
                    
                    # Disable application date if situation is Not Applied
                    application_date_disabled = permit_situation == "Not Applied"
                    st.date_input(
                        "Application Date",
                        format="MM/DD/YYYY",
                        key="edit_permit_application_date",
                        disabled=application_date_disabled
                    )
                    
                    # Disable issue date if situation is Not Applied or Applied
                    issue_date_disabled = permit_situation in ["Not Applied", "Applied"]
                    st.date_input(
                        "Issue Date",
                        format="MM/DD/YYYY",
                        key="edit_permit_issue_date",
                        disabled=issue_date_disabled
                    )
                    
                    st.text_area(
                        "Observation",
                        key="edit_permit_observation",
                        placeholder="Enter any additional notes"
                    )
                
                col1, col2 = st.columns(2)
                with col1:
                    st.button(
                        "Cancel",
                        key="cancel_edit",
                        on_click=lambda: setattr(st.session_state, 'show_permit_modal', False)
                    )
                with col2:
                    st.button(
                        "Save Changes",
                        key="save_edit",
                        type="primary",
                        on_click=save_edited_permit
                    )
    
    with tab3:
        st.write("Select a permit to delete.")
        
        # Lot/Address selector
        lot_addresses = sorted(df["LOT/ADDRESS"].dropna().unique())
        selected_lot = st.selectbox(
            "Select Lot/Address",
            options=lot_addresses,
            index=None,
            key="delete_lot_address",
            placeholder="Select a permit to delete"
        )
        
        if selected_lot:
            # Get permit data
            permit_data = df[df["LOT/ADDRESS"] == selected_lot].iloc[0]
            
            st.write("**Permit Details:**")
            st.write(f"**Model:** {permit_data['Model']}")
            st.write(f"**Jobsite:** {permit_data['Jobsite']}")
            st.write(f"**Situation:** {permit_data['Situation']}")
            
            # Handle Request Date
            request_date = pd.to_datetime(permit_data['Request Date'], errors='coerce')
            st.write(f"**Request Date:** {request_date.strftime('%m/%d/%Y') if pd.notna(request_date) else 'N/A'}")
            
            # Handle Application Date
            application_date = pd.to_datetime(permit_data['Application Date'], errors='coerce')
            st.write(f"**Application Date:** {application_date.strftime('%m/%d/%Y') if pd.notna(application_date) else 'N/A'}")
            
            # Handle Issue Date
            issue_date = pd.to_datetime(permit_data['Issue Date'], errors='coerce')
            st.write(f"**Issue Date:** {issue_date.strftime('%m/%d/%Y') if pd.notna(issue_date) else 'N/A'}")
            
            if pd.notna(permit_data['Observation']):
                st.write(f"**Observation:** {permit_data['Observation']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.button(
                    "Cancel",
                    key="cancel_delete",
                    on_click=lambda: setattr(st.session_state, 'show_permit_modal', False)
                )
            with col2:
                st.button(
                    "Delete Permit",
                    key="confirm_delete",
                    type="primary",
                    on_click=delete_selected_permit
                ) 