import streamlit as st
import pandas as pd
from datetime import datetime
from database.database_timesheet_analysis import load_data, sync_and_reload, add_register, add_user
from utils.st_custom import st_custom_table
import json
import os
from database.mongodb_utils import get_collection_data, insert_document, update_document, delete_document

# Copiado de modal_admin_timesheet_analysis.py
# TODO: Adicionar tabs para Monthly Highlights, Opportunities e Action Plans

def initialize_modal_session_state():
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = datetime.today()
    if "selected_name" not in st.session_state:
        st.session_state.selected_name = None
    if "selected_error" not in st.session_state:
        st.session_state.selected_error = None
    if "team_for_name" not in st.session_state:
        st.session_state.team_for_name = ""
    if "corporation_for_name" not in st.session_state:
        st.session_state.corporation_for_name = ""
    if "payrate_for_name" not in st.session_state:
        st.session_state.payrate_for_name = 0.0
    if "adding_h" not in st.session_state:
        st.session_state.adding_h = 0.0
    if "removing_h" not in st.session_state:
        st.session_state.removing_h = 0.0
    if "adding_v" not in st.session_state:
        st.session_state.adding_v = 0.0
    if "removing_v" not in st.session_state:
        st.session_state.removing_v = 0.0
    if "total_reallocated" not in st.session_state:
        st.session_state.total_reallocated = 0.0
    if "signup_name" not in st.session_state:
        st.session_state.signup_name = ""
    if "signup_payrate" not in st.session_state:
        st.session_state.signup_payrate = 0.0
    if "signup_corporation" not in st.session_state:
        st.session_state.signup_corporation = ""
    if "signup_team" not in st.session_state:
        st.session_state.signup_team = ""
    if "signup_login" not in st.session_state:
        st.session_state.signup_login = ""
    if "signup_password" not in st.session_state:
        st.session_state.signup_password = ""
    if "signup_confirm_password" not in st.session_state:
        st.session_state.signup_confirm_password = ""

def data_match():
    nome = st.session_state.selected_name
    df_t1, df_t2 = load_data()
    match = df_t2[df_t2["nome_t2"] == nome]
    if not match.empty:
        st.session_state.team_for_name = match.iloc[0]["team_t2"]
        st.session_state.corporation_for_name = match.iloc[0]["empresa_t2"]
        st.session_state.payrate_for_name = float(match.iloc[0]["usd_hours_t2"])
    else:
        st.session_state.team_for_name = ""
        st.session_state.corporation_for_name = ""
        st.session_state.payrate_for_name = 0.0

def calcular_add():
    payrate = st.session_state.payrate_for_name
    hour = st.session_state.adding_h
    removed = st.session_state.removing_v

    st.session_state.removing_v = 0.0
    if hour > 0.0:
        value = hour * payrate
        st.session_state.total_reallocated = value + removed
        st.session_state.adding_v = value
    else:
        st.session_state.total_reallocated = 0.0 + removed
        st.session_state.adding_v = 0.0

def calcular_rem():
    payrate = st.session_state.payrate_for_name
    hour = st.session_state.removing_h
    added = st.session_state.adding_v

    st.session_state.adding_v = 0.0
    if hour > 0.0:
        value = hour * payrate
        st.session_state.total_reallocated = value + added
        st.session_state.removing_v = value
    else:
        st.session_state.total_reallocated = 0.0 + added
        st.session_state.removing_v = 0.0

def add_and_refresh_register():
    try:
        date = st.session_state.get("selected_date", datetime.today())
        name = st.session_state.get("selected_name", "")
        error = st.session_state.get("selected_error", "")
        team = st.session_state.get("team_for_name", "")
        corporation = st.session_state.get("corporation_for_name", "")
        payrate = st.session_state.get("payrate_for_name", 0.0)
        add_hours = st.session_state.get("adding_h", 0.0)
        remove_hours = st.session_state.get("removing_h", 0.0)
        add_value = add_hours * payrate
        remove_value = remove_hours * payrate
        total = add_value + remove_value
        if not name or not team or not corporation:
            st.error("Please fill in all required fields")
            return
        if add_register(date, name, error, team, corporation, add_hours, remove_hours, add_value, remove_value, total):
            st.session_state.selected_date = datetime.today()
            st.session_state.selected_name = None
            st.session_state.selected_error = None
            st.session_state.team_for_name = ""
            st.session_state.corporation_for_name = ""
            st.session_state.payrate_for_name = 0.0
            st.session_state.adding_h = 0.0
            st.session_state.removing_h = 0.0
            st.session_state.adding_v = 0.0
            st.session_state.removing_v = 0.0
            st.session_state.total_reallocated = 0.0
            sync_and_reload()
            st.success("Register added successfully!")
            st.session_state['show_manage_modal'] = False
        else:
            st.error("Failed to add register")
    except Exception as e:
        st.error(f"Error adding register: {str(e)}")

def add_user_to_authorized_users_json(name, corporation, payrate, team, login, password):
    path = os.path.join("utils", "authorized_users.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for user in data["users"]:
        if user["login"] == login:
            return False, "Login já cadastrado."
    new_user = {
        "login": login,
        "name": name,
        "password": password,
        "roles": ["user"],
        "screens": [
            "timesheet_analysis",
            "permit_control",
            "accounting_indicators",
            "it_projects"
        ]
    }
    data["users"].append(new_user)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return True, "Usuário cadastrado com sucesso."

def add_and_refresh_user():
    try:
        name = st.session_state.get("signup_name", "")
        corporation = st.session_state.get("signup_corporation", "")
        payrate = st.session_state.get("signup_payrate", 0.0)
        team = st.session_state.get("signup_team", "")
        login = st.session_state.get("signup_login", "")
        password = st.session_state.get("signup_password", "")
        confirm_password = st.session_state.get("signup_confirm_password", "")
        if not name or not corporation or not team or not login or not password or not confirm_password:
            st.error("Please fill in all required fields")
            return
        if password != confirm_password:
            st.error("Passwords do not match!")
            return
        ok, msg = add_user_to_authorized_users_json(name, corporation, payrate, team, login, password)
        if not ok:
            st.error(msg)
            return
        if add_user(name, payrate, corporation, team):
            st.session_state.signup_name = ""
            st.session_state.signup_payrate = 0.0
            st.session_state.signup_corporation = ""
            st.session_state.signup_team = ""
            st.session_state.signup_login = ""
            st.session_state.signup_password = ""
            st.session_state.signup_confirm_password = ""
            sync_and_reload()
            st.success("User added successfully!")
            st.session_state['show_manage_modal'] = False
        else:
            st.error("Failed to add user")
    except Exception as e:
        st.error(f"Error adding user: {str(e)}")

@st.dialog("Manage Timesheet Data", width="large")
def modal():
    initialize_modal_session_state()
    df_t1, df_t2 = load_data()
    st.write("Choose a tab to manage.")
    tab_names = ["Registers", "Users", "Monthly Highlights", "Opportunities", "Action Plans"]
    Registers, Users, Highlights, Opportunities, ActionPlans = st.tabs(tab_names)

    with Registers:
        with st.expander("Add a new Register", expanded=False):
            with st.container(border=False):
                st.subheader("Informations")
                col1, col2 = st.columns([2, 8])
                with col1:
                    selected_date = st.date_input("Date", format="MM/DD/YYYY", key="selected_date")
                with col2:
                    selected_name = st.selectbox(
                        "Name",
                        options=df_t2["nome_t2"].dropna().unique(),
                        index=None,
                        key="selected_name",
                        placeholder="Select a name",
                        on_change=data_match,
                    )
                col1, col2, col3 = st.columns(3)
                with col1:
                    selected_error = st.selectbox(
                        "Error",
                        options=df_t1["error_t1"].dropna().unique(),
                        index=None,
                        placeholder="Select an error",
                        key="selected_error"
                    )
                with col2:
                    selected_team = st.text_input(
                        "Team",
                        value=st.session_state.get("team_for_name", ""),
                        key="team_for_name",
                        disabled=True
                    )
                with col3:
                    selected_corporation = st.text_input("Corporation", value=st.session_state.get("corporation_for_name", ""), key="corporation_for_name", disabled=True)
                st.divider()
                st.subheader("Values")
                col1, col2, col3 = st.columns(3)
                if "adding_h" not in st.session_state:
                    st.session_state["adding_h"] = 0.0
                if "removing_h" not in st.session_state:
                    st.session_state["removing_h"] = 0.0
                if "payrate_for_name" not in st.session_state:
                    st.session_state["payrate_for_name"] = 0.0
                if "adding_v" not in st.session_state:
                    st.session_state["adding_v"] = 0.0
                if "removing_v" not in st.session_state:
                    st.session_state["removing_v"] = 0.0
                if "total_reallocated" not in st.session_state:
                    st.session_state["total_reallocated"] = 0.0
                with col1:
                    added_time_hour = st.number_input(
                        "Add time/hour",
                        min_value=0.0,
                        step=0.25,
                        format="%.2f",
                        key="adding_h",
                        on_change=calcular_add
                    )
                with col2:
                    removed_time_hour = st.number_input(
                        "Remove time/hour",
                        min_value=0.0,
                        step=0.25,
                        format="%.2f",
                        key="removing_h",
                        on_change=calcular_rem
                    )
                with col3:
                    payrate = st.number_input(
                        "Payrate",
                        value=float(st.session_state.get("payrate_for_name") or 0.0),
                        key="payrate_for_name",
                        disabled=True
                    )
                col1, col2, col3 = st.columns(3)
                with col1:
                    added_value = st.number_input(
                        "Add $",
                        step=0.25,
                        format="%.2f",
                        disabled=True,
                        key="adding_v"
                    )
                with col2:
                    removed_value = st.number_input(
                        "Remove $",
                        step=0.25,
                        format="%.2f",
                        disabled=True,
                        key="removing_v"                        
                    )
                with col3:
                    total = st.number_input(
                        "Total",
                        step=0.25,
                        format="%.2f",
                        disabled=True,
                        key="total_reallocated"
                    )
                st.button("Add Register", key="add_register", type="primary", on_click=add_and_refresh_register)
        with st.expander("Register List", expanded=True):
            col1, col2 = st.columns([8, 1], vertical_alignment="center", gap="large")
            with col1:
                st.subheader("Dados T1")
            with col2:
                if st.button(":material/sync:", key="sync_t1", help="Click to refresh", type='secondary'):
                    df_t1, df_t2 = sync_and_reload()
            st.dataframe(df_t1.sort_values(by="date_t1", ascending=False), use_container_width=True, hide_index=True)
    with Users:
        with st.expander("Add a new Worker", expanded=False):
            with st.container(border=False):
                st.subheader("Informations")
                col1, col2 = st.columns([2, 1])
                with col1:
                    newName = st.text_input(
                        "Name",
                        key="signup_name",
                        placeholder="Insert a name",
                    )
                with col2:
                    newPayrate = st.number_input(
                        "Payrate ($)", 
                        key="signup_payrate", 
                        min_value=0.0,
                        value=None,
                        step=1.0
                    )
                col1, col2 = st.columns([2, 1])
                with col1:
                    newCompany = st.selectbox(
                        "Company",
                        options=df_t2["empresa_t2"].dropna().unique(),
                        index=None,
                        placeholder="Select a company",
                        key="signup_corporation",
                        accept_new_options=True
                    )
                with col2:
                    newTeam = st.selectbox(
                        "Team",
                        options=df_t2["team_t2"].dropna().unique(),
                        index=None,
                        key="signup_team",
                        accept_new_options=True,
                        placeholder="Choose a team"
                    )
                st.text_input("Login (e-mail)", key="signup_login", placeholder="Enter e-mail")
                st.text_input("Password", key="signup_password", type="password", placeholder="Enter password")
                st.text_input("Confirm Password", key="signup_confirm_password", type="password", placeholder="Repeat password")
                st.button("Add User",
                          key="add_user",
                          type="primary",
                          on_click=add_and_refresh_user
                        )
        with st.expander("Register List", expanded=True):
            col1, col2 = st.columns([8, 1], vertical_alignment="center", gap="large")
            with col1:
                st.subheader("Dados T2")
            with col2:
                if st.button(":material/sync:", key="sync_register", help="Click to refresh", type='secondary'):
                    df_t1, df_t2 = sync_and_reload()
            st.dataframe(df_t2.dropna().sort_values(by=df_t2.columns[0]), use_container_width=True, hide_index=True)
    with Highlights:
        st.subheader("Monthly Highlights CRUD")
        # Seleção de ano/mês
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2000, max_value=2100, value=datetime.now().year, step=1, key="highlight_year")
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=datetime.now().month, step=1, key="highlight_month")
        # Listar highlights existentes
        highlights = get_collection_data('monthly_highlights')
        filtered = [h for h in highlights if h.get('year') == year and h.get('month') == month]
        st.write("## Highlights for selected month/year")
        for idx, h in enumerate(filtered):
            with st.expander(f"Highlight {idx+1}"):
                st.json(h)
                col_edit, col_delete = st.columns(2)
                with col_edit:
                    if st.button(f"Edit", key=f"edit_highlight_{idx}"):
                        st.info("TODO: Edit form here")
                with col_delete:
                    if st.button(f"Delete", key=f"delete_highlight_{idx}"):
                        if delete_document('monthly_highlights', {'year': year, 'month': month, 'positive': h.get('positive'), 'negative': h.get('negative')}):
                            st.success("Deleted!")
        st.divider()
        st.write("## Add new Highlight")
        if st.button("Add Highlight", key="add_highlight_btn"):
            st.info("TODO: Add form here")
    with Opportunities:
        st.subheader("Opportunities CRUD")
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2000, max_value=2100, value=datetime.now().year, step=1, key="opp_year")
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=datetime.now().month, step=1, key="opp_month")
        opportunities = get_collection_data('monthly_opportunities')
        filtered = [o for o in opportunities if o.get('year') == year and o.get('month') == month]
        st.write("## Opportunities for selected month/year")
        for idx, o in enumerate(filtered):
            with st.expander(f"Opportunity {idx+1}"):
                st.json(o)
                col_edit, col_delete = st.columns(2)
                with col_edit:
                    if st.button(f"Edit", key=f"edit_opp_{idx}"):
                        st.info("TODO: Edit form here")
                with col_delete:
                    if st.button(f"Delete", key=f"delete_opp_{idx}"):
                        if delete_document('monthly_opportunities', {'year': year, 'month': month, 'opportunity_list': o.get('opportunity_list')}):
                            st.success("Deleted!")
        st.divider()
        st.write("## Add new Opportunity")
        if st.button("Add Opportunity", key="add_opp_btn"):
            st.info("TODO: Add form here")
    with ActionPlans:
        st.subheader("Action Plans CRUD")
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2000, max_value=2100, value=datetime.now().year, step=1, key="plan_year")
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=datetime.now().month, step=1, key="plan_month")
        plans = get_collection_data('action_plans')
        filtered = [p for p in plans if hasattr(p.get('created_at', None), 'year') and p['created_at'].year == year and p['created_at'].month == month]
        st.write("## Action Plans for selected month/year")
        for idx, p in enumerate(filtered):
            with st.expander(f"Action Plan {idx+1}"):
                st.json(p)
                col_edit, col_delete = st.columns(2)
                with col_edit:
                    if st.button(f"Edit", key=f"edit_plan_{idx}"):
                        st.info("TODO: Edit form here")
                with col_delete:
                    if st.button(f"Delete", key=f"delete_plan_{idx}"):
                        if delete_document('action_plans', {'title': p.get('title'), 'created_at': p.get('created_at')}):
                            st.success("Deleted!")
        st.divider()
        st.write("## Add new Action Plan")
        if st.button("Add Action Plan", key="add_plan_btn"):
            st.info("TODO: Add form here") 