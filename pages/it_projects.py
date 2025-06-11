import streamlit as st
import logging

logger = logging.getLogger(__name__)

def show_screen(user_data):
    """Main function to display the TI screen"""
    st.header("IT Projects")
    
    # Show admin controls only for ti_admin role
    if "ti_admin" in user_data.get("roles", []):
        st.button(":material/draw: Manage IT", key="manage_ti_button", type='secondary')
    
    # Placeholder content
    st.info("IT management module coming soon!")
    
    # Example of role-based content
    if "ti_admin" in user_data.get("roles", []):
        st.write("As an IT admin, you will be able to:")
        st.write("- Manage system configurations")
        st.write("- Monitor system health")
        st.write("- Handle user support tickets")
    else:
        st.write("As a regular user, you will be able to:")
        st.write("- Submit support tickets")
        st.write("- View system status")
        st.write("- Access IT documentation") 