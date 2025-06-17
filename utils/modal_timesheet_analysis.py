import streamlit as st
import pandas as pd
from datetime import datetime
from database.database_timesheet_analysis import load_data, sync_and_reload, add_register, add_user
from antique.st_custom import st_custom_table
from database.mongodb_utils import get_collection_data, insert_document, update_document, delete_document
import json
import os

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

def set_active_tab(tab_name):
    st.session_state['active_modal_tab'] = tab_name

def get_active_tab(tab_names):
    return st.session_state.get('active_modal_tab', tab_names[0])

# Define the dialog function at module level
@st.dialog("Manage Timesheet Data", width="large")
def _modal_dialog():
    initialize_modal_session_state()
    df_t1, df_t2 = load_data()
    st.write("Choose a tab to manage.")
    tab_names = ["Registers", "Users", "Monthly Highlights", "Opportunities", "Action Plans"]
    # Controle de aba ativa
    if 'active_modal_tab' not in st.session_state:
        st.session_state['active_modal_tab'] = tab_names[0]
    active_tab_idx = tab_names.index(st.session_state['active_modal_tab']) if st.session_state['active_modal_tab'] in tab_names else 0
    selected_tabs = st.tabs(tab_names)
    tab_map = dict(zip(tab_names, selected_tabs))

    # Helper for popover confirmation
    def confirm_delete(label, on_confirm, key):
        with st.popover(label):
            st.write("Are you sure you want to delete?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(":material/check: Yes", key=f"{key}_yes"):
                    on_confirm()
                    st.rerun()
            with col2:
                if st.button(":material/close: No", key=f"{key}_no"):
                    st.session_state['modal_open'] = False
                    st.rerun()

    with tab_map["Registers"]:
        set_active_tab("Registers")
        with st.expander("Add a new Register", expanded=False):
            with st.container(border=False):
                st.subheader("Information")
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
                    selected_corporation = st.text_input("Company", value=st.session_state.get("corporation_for_name", ""), key="corporation_for_name", disabled=True)
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
                        "USD/hours",
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
                st.button(":material/add: Add Register", key="add_register", type="primary", on_click=add_and_refresh_register)
        with st.expander("Register List", expanded=True):
            col1, col2 = st.columns([8, 1], vertical_alignment="center", gap="large")
            with col1:
                st.subheader("T1 Data")
            with col2:
                if st.button(":material/sync:", key="sync_t1", help="Click to refresh", type='secondary'):
                    df_t1, df_t2 = sync_and_reload()
                    st.rerun()
            st.dataframe(df_t1.sort_values(by="date_t1", ascending=False), use_container_width=True, hide_index=True)
    with tab_map["Users"]:
        set_active_tab("Users")
        with st.expander("Add a new Worker", expanded=False):
            with st.container(border=False):
                st.subheader("Information")
                col1, col2 = st.columns([2, 1])
                with col1:
                    newName = st.text_input(
                        "Name",
                        key="signup_name",
                        placeholder="Insert a name",
                    )
                with col2:
                    newPayrate = st.number_input(
                        "USD/hours", 
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
                st.button(":material/add: Add User", key="add_user", type="primary", on_click=add_and_refresh_user)
        with st.expander("Worker List", expanded=True):
            col1, col2 = st.columns([8, 1], vertical_alignment="center", gap="large")
            with col1:
                st.subheader("T2 Data")
            with col2:
                if st.button(":material/sync:", key="sync_register", help="Click to refresh", type='secondary'):
                    df_t1, df_t2 = sync_and_reload()
                    st.rerun()
            st.dataframe(df_t2.dropna().sort_values(by=df_t2.columns[0]), use_container_width=True, hide_index=True)
    with tab_map["Monthly Highlights"]:
        set_active_tab("Monthly Highlights")
        years = sorted({h.get('year') for h in get_collection_data('monthly_highlights') if h.get('year')})
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Year", options=years, index=years.index(datetime.now().year) if datetime.now().year in years else 0, key="highlight_year", on_change=lambda: set_active_tab("Monthly Highlights"))
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=st.session_state.get("highlight_month", datetime.now().month), step=1, key="highlight_month", on_change=lambda: set_active_tab("Monthly Highlights"))
        highlights = get_collection_data('monthly_highlights')
        filtered = [h for h in highlights if h.get('year') == year and h.get('month') == month]
        st.write("### Highlights for selected month/year")
        if filtered:
            h = filtered[0]
            pos = st.text_area("Positives (one per line)", value="\n".join([p.get('title','') for p in h.get('positive', [])]), key=f"edit_highlight_pos")
            neg = st.text_area("Negatives (one per line)", value="\n".join([n.get('title','') for n in h.get('negative', [])]), key=f"edit_highlight_neg")
            if st.button(":material/save: Save", key=f"save_highlight"):
                update_document('monthly_highlights', {'year': year, 'month': month}, {
                    'year': year,
                    'month': month,
                    'positive': [{'title': t.strip()} for t in pos.splitlines() if t.strip()],
                    'negative': [{'title': t.strip()} for t in neg.splitlines() if t.strip()]
                })
                st.success("Updated!")
                st.rerun()
            confirm_delete(":material/delete: Delete", lambda: (delete_document('monthly_highlights', {'year': year, 'month': month}), st.success("Deleted!"), st.rerun()), key=f"popover_highlight")
        else:
            with st.form(key="add_highlight_form"):
                pos_new = st.text_area("Positives (one per line)", key="add_highlight_pos")
                neg_new = st.text_area("Negatives (one per line)", key="add_highlight_neg")
                submitted = st.form_submit_button(":material/add: Save Highlight")
                if submitted:
                    insert_document('monthly_highlights', {
                        'year': year,
                        'month': month,
                        'positive': [{'title': t.strip()} for t in pos_new.splitlines() if t.strip()],
                        'negative': [{'title': t.strip()} for t in neg_new.splitlines() if t.strip()]
                    })
                    st.success("Added!")
                    st.rerun()
    with tab_map["Opportunities"]:
        set_active_tab("Opportunities")
        years = sorted({o.get('year') for o in get_collection_data('monthly_opportunities') if o.get('year')})
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Year", options=years, index=years.index(datetime.now().year) if datetime.now().year in years else 0, key="opp_year", on_change=lambda: set_active_tab("Opportunities"))
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=st.session_state.get("opp_month", datetime.now().month), step=1, key="opp_month", on_change=lambda: set_active_tab("Opportunities"))
        opportunities = get_collection_data('monthly_opportunities')
        filtered = [o for o in opportunities if o.get('year') == year and o.get('month') == month]
        st.write("### Opportunities for selected month/year")
        if filtered:
            o = filtered[0]
            opp_blocks = o.get('opportunity_list', [])
            titles = []
            challenges = []
            improvements = []
            for bidx, block in enumerate(opp_blocks):
                titles.append(st.text_input(f"Title", value=block.get('title',''), key=f"opp_title_{bidx}"))
                challenges.append(st.text_area(f"Challenges (one per line)", value="\n".join(block.get('challenges',[])), key=f"opp_challenges_{bidx}"))
                improvements.append(st.text_area(f"Improvements (one per line)", value="\n".join(block.get('improvements',[])), key=f"opp_improvements_{bidx}"))
            if st.button(":material/save: Save", key=f"save_opp"):
                new_blocks = []
                for i in range(len(opp_blocks)):
                    new_blocks.append({
                        'title': titles[i],
                        'challenges': [c.strip() for c in challenges[i].splitlines() if c.strip()],
                        'improvements': [im.strip() for im in improvements[i].splitlines() if im.strip()]
                    })
                update_document('monthly_opportunities', {'year': year, 'month': month}, {
                    'year': year,
                    'month': month,
                    'opportunity_list': new_blocks
                })
                st.success("Updated!")
                st.rerun()
            confirm_delete(":material/delete: Delete", lambda: (delete_document('monthly_opportunities', {'year': year, 'month': month}), st.success("Deleted!"), st.rerun()), key=f"popover_opp")
        else:
            with st.form(key="add_opp_form"):
                title_new = st.text_input("Title", key="add_opp_title")
                challenges_new = st.text_area("Challenges (one per line)", key="add_opp_challenges")
                improvements_new = st.text_area("Improvements (one per line)", key="add_opp_improvements")
                submitted = st.form_submit_button(":material/add: Save Opportunity")
                if submitted:
                    if not title_new.strip() or not challenges_new.strip() or not improvements_new.strip():
                        st.error("Title, Challenges, and Improvements are required.")
                    else:
                        insert_document('monthly_opportunities', {
                            'year': year,
                            'month': month,
                            'opportunity_list': [{
                                'title': title_new,
                                'challenges': [c.strip() for c in challenges_new.splitlines() if c.strip()],
                                'improvements': [i.strip() for i in improvements_new.splitlines() if i.strip()]
                            }]
                        })
                        st.success("Added!")
                        st.rerun()
    with tab_map["Action Plans"]:
        set_active_tab("Action Plans")
        years = sorted({p.get('created_at').year for p in get_collection_data('action_plans') if p.get('created_at') and hasattr(p.get('created_at'), 'year')})
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Year", options=years, index=years.index(datetime.now().year) if datetime.now().year in years else 0, key="plan_year", on_change=lambda: set_active_tab("Action Plans"))
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=st.session_state.get("plan_month", datetime.now().month), step=1, key="plan_month", on_change=lambda: set_active_tab("Action Plans"))
        plans = get_collection_data('action_plans')
        filtered = [p for p in plans if hasattr(p.get('created_at', None), 'year') and p['created_at'].year == year and p['created_at'].month == month]
        st.write("### Action Plan for selected month/year")
        # Helper to manage subplans/actions in session_state
        def get_plan_state():
            key = f"plan_state_{year}_{month}"
            if key not in st.session_state:
                if filtered:
                    st.session_state[key] = filtered[0].copy()
                else:
                    st.session_state[key] = {
                        'title': '',
                        'description': '',
                        'created_at': datetime(year, month, 1),
                        'subplans': []
                    }
            return st.session_state[key]
        plan_state = get_plan_state()
        # Plan fields
        with st.container(border=True):
            st.markdown("#### :material/assignment: Plan Details")
            col1, col2 = st.columns(2)
            with col1:
                plan_state['title'] = st.text_input("Title", value=plan_state.get('title',''), key=f"plan_title")
            with col2:
                plan_state['description'] = st.text_area("Description", value=plan_state.get('description',''), key=f"plan_desc")
        # Subplans
        st.markdown("---")
        st.markdown(":material/list: **Subplans**")
        subplan_changed = False  # Flag para controlar alterações
        for sidx, sub in enumerate(plan_state['subplans']):
            with st.container(border=True):
                scol1, scol2, scol3, scol4 = st.columns([2.2,2.6,1.2,1], vertical_alignment="center")
                with scol1:
                    sub['title'] = st.text_area("Subplan Title", value=sub.get('title',''), key=f"subplan_title_{sidx}")
                with scol2:
                    sub['reason'] = st.text_area("Reason", value=sub.get('reason',''), key=f"subplan_reason_{sidx}")
                with scol3:
                    sub['start_date'] = st.date_input("Start Date", value=pd.to_datetime(sub.get('start_date')) if sub.get('start_date') else datetime(year, month, 1), key=f"subplan_start_{sidx}")
                    sub['end_date'] = st.date_input("End Date", value=pd.to_datetime(sub.get('end_date')) if sub.get('end_date') else datetime(year, month, 1), key=f"subplan_end_{sidx}")
                with scol4:
                    if st.button(":material/delete:", key=f"remove_subplan_{sidx}"):
                        plan_state['subplans'].pop(sidx)
                        subplan_changed = True
                st.markdown(":material/list_alt: **Actions**")
                action_changed = False  # Flag para ações
                for aidx, a in enumerate(sub.get('actions', [])):
                    with st.container(border=True):
                        ac1, ac2, ac3, ac4, ac5 = st.columns([3,1.5,1.75,1.75,1], vertical_alignment="center")
                        with ac1:
                            a['title'] = st.text_input("Action Title", value=a.get('title',''), key=f"action_title_{sidx}_{aidx}")
                        with ac2:
                            a['status'] = st.text_input("Status", value=a.get('status',''), key=f"action_status_{sidx}_{aidx}")
                        with ac3:
                            a['due_date'] = st.date_input("Due Date", value=pd.to_datetime(a.get('due_date')) if a.get('due_date') else datetime(year, month, 1), key=f"action_due_{sidx}_{aidx}")
                        with ac4:
                            a['responsible'] = st.text_input("Responsible", value=a.get('responsible',''), key=f"action_resp_{sidx}_{aidx}")
                        with ac5:
                            if st.button(":material/delete:", key=f"remove_action_{sidx}_{aidx}"):
                                sub['actions'].pop(aidx)
                                action_changed = True
                if action_changed:
                    st.rerun()
                if st.button(":material/add: Add Action", key=f"add_action_{sidx}"):
                    if 'actions' not in sub:
                        sub['actions'] = []
                    sub['actions'].append({
                        'title': '', 'status': '', 'due_date': datetime(year, month, 1), 'responsible': ''
                    })
                    st.rerun()
        if subplan_changed:
            st.rerun()
        if st.button(":material/add: Add Subplan", key="add_subplan"):
            plan_state['subplans'].append({
                'title': '', 'reason': '', 'start_date': datetime(year, month, 1), 'end_date': datetime(year, month, 1), 'actions': []
            })
            st.rerun()
        st.markdown("---")
        col_save, col_delete = st.columns([2,1]); save_success = False
        with col_save:
            if st.button(":material/save: Save Action Plan", key=f"save_plan", type="primary"):
                # Validação mínima
                if not plan_state.get('title'):
                    st.error("O título do plano é obrigatório.")
                else:
                    def ensure_datetime(obj):
                        if isinstance(obj, datetime):
                            return obj
                        elif hasattr(obj, 'year') and hasattr(obj, 'month') and hasattr(obj, 'day'):
                            return datetime(obj.year, obj.month, obj.day)
                        return obj
                    for sub in plan_state['subplans']:
                        sub['start_date'] = ensure_datetime(sub.get('start_date'))
                        sub['end_date'] = ensure_datetime(sub.get('end_date'))
                        for a in sub.get('actions', []):
                            a['due_date'] = ensure_datetime(a.get('due_date'))
                    plan_state['created_at'] = ensure_datetime(plan_state.get('created_at'))
                    try:
                        update_document('action_plans', {'title': plan_state.get('title'), 'created_at': plan_state.get('created_at')}, plan_state)
                        st.success("Updated!")
                        save_success = True
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
        with col_delete:
            def delete_plan():
                try:
                    delete_document('action_plans', {'title': plan_state.get('title'), 'created_at': plan_state.get('created_at')})
                    st.success("Deleted!")
                    st.session_state['modal_open'] = False
                    st.session_state['show_manage_modal'] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao deletar: {e}")
            confirm_delete(":material/delete: Delete", delete_plan, key=f"popover_plan")
        if not filtered:
            st.info("No Action Plan for this month/year. Fill the fields above to create one.")
            if st.button(":material/add: Create Action Plan", key="create_plan"):
                # Validação mínima
                if not plan_state.get('title'):
                    st.error("O título do plano é obrigatório.")
                else:
                    def ensure_datetime(obj):
                        if isinstance(obj, datetime):
                            return obj
                        elif hasattr(obj, 'year') and hasattr(obj, 'month') and hasattr(obj, 'day'):
                            return datetime(obj.year, obj.month, obj.day)
                        return obj
                    for sub in plan_state['subplans']:
                        sub['start_date'] = ensure_datetime(sub.get('start_date'))
                        sub['end_date'] = ensure_datetime(sub.get('end_date'))
                        for a in sub.get('actions', []):
                            a['due_date'] = ensure_datetime(a.get('due_date'))
                    plan_state['created_at'] = ensure_datetime(plan_state.get('created_at'))
                    try:
                        insert_document('action_plans', plan_state)
                        st.success("Created!")
                        st.session_state['modal_open'] = False
                        st.session_state['show_manage_modal'] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar: {e}")
        # Só fechar o modal após salvar/deletar/criar
        if save_success:
            st.session_state['modal_open'] = False
            st.session_state['show_manage_modal'] = False
            st.rerun()

def show_manage_modal():
    """Exibe o modal de gerenciamento de dados, controlando tudo por tabs internas. Garante exclusividade de dialog."""
    # Lock global para garantir que só um dialog decorado seja chamado
    if st.session_state.get('_dialog_lock', None) not in (None, 'manage'):
        return
    if st.session_state.get('show_manage_modal', False):
        st.session_state['_dialog_lock'] = 'manage'
        _modal_dialog()
        st.session_state['_dialog_lock'] = None