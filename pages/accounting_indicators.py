import streamlit as st
import logging

logger = logging.getLogger(__name__)

def show_screen(user_data):
    """Main function to display the accounting screen"""
    st.header("Accounting Indicators")
    
    # Show admin controls only for accounting_admin role
    if "accounting_admin" in user_data.get("roles", []):
        st.button(":material/draw: Manage Accounting", key="manage_accounting_button", type='secondary')
    
    # Placeholder content
    st.info("Accounting management module coming soon!")
    
    # Example of role-based content
    if "accounting_admin" in user_data.get("roles", []):
        st.write("As an accounting admin, you will be able to:")
        st.write("- Manage financial records")
        st.write("- Generate financial reports")
        st.write("- Track expenses and revenue")
    else:
        st.write("As a regular user, you will be able to:")
        st.write("- View financial summaries")
        st.write("- Access expense reports")
        st.write("- Track budget allocations") 