import streamlit as st
import json
import logging

logger = logging.getLogger(__name__)

@st.dialog("Edit Profile", width="medium")
def user_change_data_modal():
    current_user = st.session_state['user_data']
    current_name = current_user['name']

    with st.form("edit_profile_form"):
        new_name = st.text_input("Name", value=current_name)
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Save Changes")
        if submitted:
            if new_password and new_password != confirm_password:
                st.error("Passwords do not match!")
                return
            try:
                with open("utils/authorized_users.json", "r", encoding='utf-8') as file:
                    data = json.load(file)
                for user in data["users"]:
                    if user["login"] == current_user["login"]:
                        user["name"] = new_name
                        if new_password:
                            user["password"] = new_password
                        break
                with open("utils/authorized_users.json", "w", encoding='utf-8') as file:
                    json.dump(data, file, indent=4)
                st.session_state['user_data']['name'] = new_name
                if new_password:
                    st.session_state['user_data']['password'] = new_password
                st.success("Profile updated successfully!")
                st.rerun()
            except Exception as e:
                logger.error(f"Error updating profile: {str(e)}")
                st.error("Error updating profile. Please try again.") 