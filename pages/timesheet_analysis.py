import streamlit as st
import altair as alt
import pandas as pd
from datetime import datetime
import logging
from database.database_timesheet_analysis import *
from utils.st_custom import *
from utils.modal_admin_timesheet_analysis import modal

logger = logging.getLogger(__name__)

def initialize_session_state():
    """Initialize session state variables for timesheet analysis"""
    if 'start_date' not in st.session_state:
        st.session_state['start_date'] = None
    if 'end_date' not in st.session_state:
        st.session_state['end_date'] = None
    if 'corporation_select' not in st.session_state:
        st.session_state['corporation_select'] = "All"
    if 'checkbox_states' not in st.session_state:
        st.session_state['checkbox_states'] = {}
    if 'teams_state' not in st.session_state:
        st.session_state.teams_state = {}
    if 'select_all_teams' not in st.session_state:
        st.session_state.select_all_teams = True
    if 'select_all_errors' not in st.session_state:
        st.session_state['select_all_errors'] = True
    if 'total_errors' not in st.session_state:
        st.session_state['total_errors'] = 0
    if 'added_value' not in st.session_state:
        st.session_state['added_value'] = 0
    if 'saved_value' not in st.session_state:
        st.session_state['saved_value'] = 0
    if 'total_value' not in st.session_state:
        st.session_state['total_value'] = 0
    if 'filtered_df_t1' not in st.session_state:
        st.session_state['filtered_df_t1'] = None
    if 'filtered_df_t2' not in st.session_state:
        st.session_state['filtered_df_t2'] = None
    if 'view_mode' not in st.session_state:
        st.session_state['view_mode'] = "Absolute Values"

def apply_filters(df_t1, df_t2):
    """Apply all filters to the dataframes and update session state"""
    filtered_df_t1 = df_t1.copy()
    filtered_df_t2 = df_t2.copy()

    # Apply date filter
    filtered_df_t1 = filtered_df_t1[
        (filtered_df_t1["date_t1"] >= pd.to_datetime(st.session_state['start_date'])) &
        (filtered_df_t1["date_t1"] <= pd.to_datetime(st.session_state['end_date']))
    ]

    # Apply corporation filter
    if st.session_state['corporation_select'] != "All":
        filtered_df_t1 = filtered_df_t1[filtered_df_t1["corporation_t1"] == st.session_state['corporation_select']]
        filtered_df_t2 = filtered_df_t2[filtered_df_t2["empresa_t2"] == st.session_state['corporation_select']]

    # Apply team filter
    selected_teams = [team for team, checked in st.session_state.teams_state.items() if checked]
    if selected_teams:
        filtered_df_t1 = filtered_df_t1[filtered_df_t1["team_t1"].isin(selected_teams)]

    # Apply error filter
    selected_errors = [error for error, checked in st.session_state['checkbox_states'].items() if checked]
    if selected_errors:
        filtered_df_t1 = filtered_df_t1[filtered_df_t1["error_t1"].isin(selected_errors)]

    # Update session state with filtered dataframes
    st.session_state['filtered_df_t1'] = filtered_df_t1
    st.session_state['filtered_df_t2'] = filtered_df_t2

    # Update metrics
    st.session_state['total_errors'] = len(filtered_df_t1)
    st.session_state['added_value'] = filtered_df_t1['add_value_t1'].sum()
    st.session_state['saved_value'] = filtered_df_t1['remove_value_t1'].sum()
    st.session_state['total_value'] = filtered_df_t1['total_t1'].sum()

    return filtered_df_t1, filtered_df_t2

def show_screen(user_data):
    """Main function to display the timesheet analysis screen"""
    initialize_session_state()
    
    # Load data
    df_t1, df_t2 = load_data()
    if df_t1.empty or df_t2.empty:
        st.error("Error loading data. Please try again later.")
        return

    # Process data
    df_t1.columns = df_t1.columns.str.strip()
    df_t1["date_t1"] = pd.to_datetime(df_t1["date_t1"], errors="coerce")
    teams = sorted(df_t1["team_t1"].dropna().unique())
    all_errors = sorted(df_t1["error_t1"].dropna().unique())
    
    # Inicializar teams_state como dict {team: True} se ainda não estiver inicializado corretamente
    if not st.session_state.teams_state or set(st.session_state.teams_state.keys()) != set(teams):
        st.session_state.teams_state = {team: True for team in teams}
    # Inicializar checkbox_states para errors
    if not st.session_state['checkbox_states'] or set(st.session_state['checkbox_states'].keys()) != set(all_errors):
        st.session_state['checkbox_states'] = {error: True for error in all_errors}

    # Set initial dates if not set
    if st.session_state['start_date'] is None:
        st.session_state['start_date'] = pd.to_datetime(df_t1['date_t1'].min())
    if st.session_state['end_date'] is None:
        st.session_state['end_date'] = pd.to_datetime(datetime.now().date())

    # Header section
    title, view_col, manage, refresh, logout, corporation = st.columns([548, 150, 170, 66, 66, 300], gap='small', vertical_alignment="center")
    
    # Toggle By Month à esquerda do botão Manage Database
    with view_col:
        st.session_state["view_mode"] = st.toggle("By Month", value=st.session_state.get("view_mode", "Absolute Values") == "By Month", key="view_mode_toggle", label_visibility="visible")
    view_mode = "By Month" if st.session_state["view_mode"] else "Absolute Values"
    st.session_state["view_mode"] = view_mode
    with title:
        st.header("Timesheet Analysis")
    # Show manage database button only for timesheet_admin role
    with manage:
        if "timesheet_admin" in user_data.get("roles", []):
            if st.button(":material/draw: Manage Database", key="manage_button", type='secondary'):
                st.session_state['show_manage_modal'] = True
    # Chamar o modal no fluxo principal
    if st.session_state.get('show_manage_modal', False):
        modal()

    with refresh:
        if st.button(":material/sync:", key="refresh_button", help="Click to refresh", type='secondary'):
            df_t1, df_t2 = sync_and_reload()
            st.rerun()
    
    with corporation:
        corporations = ["All"] + sorted(df_t1["corporation_t1"].dropna().astype(str).unique())
        selected_corporation = st.segmented_control(
            "Select a corporation",
            options=corporations,
            key="corporation_select"
        )

    # Apply all filters and get filtered dataframes
    filtered_df_t1, filtered_df_t2 = apply_filters(df_t1, df_t2)

    # Render conteúdo conforme o modo selecionado
    if st.session_state["view_mode"] == "Absolute Values":
        show_teams_section(filtered_df_t1, teams)
        show_errors_section(filtered_df_t1)
    else:
        show_by_month_dashboard(filtered_df_t1, teams, all_errors)

def show_teams_section(filtered_df_t1, teams):
    """Display the teams analysis section"""
    filters_teams, graphs_byteam, values_byteam, totals_1 = st.columns([1, 2, 1, 1], gap='small', border=True)
    
    with filters_teams:
        st.write("Teams")
        with st.container(height=250, border=False):
            if teams:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Select all", key="select_all_teams_btn"):
                        for team in teams:
                            st.session_state.teams_state[team] = True
                            st.session_state[f"team_{team}"] = True
                        st.session_state.select_all_teams = True
                        st.rerun()
                with col_btn2:
                    if st.button("Unselect all", key="unselect_all_teams_btn"):
                        for team in teams:
                            st.session_state.teams_state[team] = False
                            st.session_state[f"team_{team}"] = False
                        st.session_state.select_all_teams = False
                        st.rerun()
                for team in teams:
                    key = f"team_{team}"
                    checked = st.checkbox(team, key=key,
                        on_change=lambda t=team: st.session_state.teams_state.update({t: st.session_state[f"team_{t}"]}))
                    st.session_state.teams_state[team] = checked
                st.session_state.select_all_teams = all(st.session_state.teams_state.values())
            else:
                st.info("No teams available.")

    # Teams graph
    with graphs_byteam:
        st.write("Errors by Team")
        team_counts = filtered_df_t1["team_t1"].value_counts().sort_values(ascending=False)
        team_counts_df = team_counts.reset_index()
        team_counts_df.columns = ["team_t1", "Count"]

        chart = alt.Chart(team_counts_df).mark_bar().encode(
            x=alt.X("team_t1:N", sort="-y", axis=alt.Axis(title=None)),
            y=alt.Y("Count:Q", axis=alt.Axis(title=None)),
            tooltip=["team_t1", "Count"]
        ).properties(
            width="container",
            height=250
        )
        st.altair_chart(chart, use_container_width=True)

    # Values by team
    with values_byteam:
        show_values_by_team(filtered_df_t1)

    # Totals section
    with totals_1:
        show_date_filters()
        st.divider()
        st.link_button(":material/view_list: Database", f"https://docs.google.com/spreadsheets/d/{DOCUMENT_ID}/edit#gid={GID_T1}", use_container_width=True)

def show_errors_section(filtered_df_t1):
    """Display the errors analysis section"""
    filtered_errors, graphs_bytype, values_bytype, totals_2 = st.columns([1, 2, 1, 1], gap='small', border=True)

    with filtered_errors:
        st.write("Errors")
        with st.container(height=250, border=False):
            all_errors = sorted(filtered_df_t1["error_t1"].dropna().unique())
            if all_errors:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Select all", key="select_all_errors_btn"):
                        for error in all_errors:
                            st.session_state['checkbox_states'][error] = True
                            st.session_state[f"error_{error}"] = True
                        st.session_state.select_all_errors = True
                        st.rerun()
                with col_btn2:
                    if st.button("Unselect all", key="unselect_all_errors_btn"):
                        for error in all_errors:
                            st.session_state['checkbox_states'][error] = False
                            st.session_state[f"error_{error}"] = False
                        st.session_state.select_all_errors = False
                        st.rerun()
                for error in all_errors:
                    key = f"error_{error}"
                    checked = st.checkbox(str(error), key=key,
                        on_change=lambda e=error: st.session_state['checkbox_states'].update({e: st.session_state[f"error_{e}"]}))
                    st.session_state['checkbox_states'][error] = checked
                st.session_state.select_all_errors = all(st.session_state['checkbox_states'].get(error, False) for error in all_errors)
            else:
                st.info("No errors available.")

    # Errors graph
    with graphs_bytype:
        st.write("Errors by Type")
        type_counts = filtered_df_t1["error_t1"].value_counts().sort_values(ascending=False)
        type_counts_df = type_counts.reset_index()
        type_counts_df.columns = ["error_t1", "Count"]

        chart = alt.Chart(type_counts_df).mark_bar().encode(
            x=alt.X("error_t1:N", sort="-y", axis=alt.Axis(title=None)),
            y=alt.Y("Count:Q", axis=alt.Axis(title=None)),
            tooltip=["error_t1", "Count"]
        ).properties(
            width="container",
            height=250
        )
        st.altair_chart(chart, use_container_width=True)

    # Values by type
    with values_bytype:
        show_values_by_type(filtered_df_t1)

    # Totals section
    with totals_2:
        show_totals(filtered_df_t1)

def show_values_by_team(filtered_df_t1):
    """Display values by team section"""
    title, desc, qty = st.columns([65, 10, 25], gap='small', vertical_alignment="center")
    with title: 
        st.write("Values by Team")
    with desc:
        st.write(":material/keyboard_double_arrow_up:")
    with qty: 
        top_n = st.number_input("", min_value=1, max_value=10, value=5, step=1, key="top_n", help="Select the number of teams to display", label_visibility="collapsed")

    df_val = filtered_df_t1.groupby("team_t1")[["add_value_t1", "remove_value_t1", "total_t1"]].sum().reset_index()
    df_val = df_val.sort_values("total_t1", ascending=False)
    df_val_top = df_val.head(top_n)
    
    df_melt = df_val_top.melt(id_vars=["team_t1", "total_t1"], value_vars=["add_value_t1", "remove_value_t1"],
                        var_name="Type", value_name="Value")

    chart_values = alt.Chart(df_melt).mark_bar().encode(
        y=alt.Y("team_t1:N", sort=list(df_val["team_t1"]), axis=alt.Axis(title=None)),
        x=alt.X("Value:Q", stack="zero", axis=alt.Axis(title=None)),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["add_value_t1", "remove_value_t1"], range=["#ff4b4b", "#0068c9"]), legend=None),
        tooltip=["team_t1", "Type", "Value"]
    ).properties(
        height=250,
        width="container"
    )

    st.altair_chart(chart_values, use_container_width=True)

def show_values_by_type(filtered_df_t1):
    """Display values by type section"""
    title, desc, qty = st.columns([65, 10, 25], gap='small', vertical_alignment="center")
    with title: 
        st.write("Values by Type")
    with desc:
        st.write(":material/keyboard_double_arrow_up:")
    with qty: 
        top_n_type = st.number_input("", min_value=1, max_value=10, value=5, step=1, key="top_n_type", help="Select the number of types to display", label_visibility="collapsed")

    df_val_type = filtered_df_t1.groupby("error_t1")[["add_value_t1", "remove_value_t1", "total_t1"]].sum().reset_index()
    df_val_type = df_val_type.sort_values("total_t1", ascending=False)
    df_val_type_top = df_val_type.head(top_n_type)

    df_melt_type = df_val_type_top.melt(id_vars=["error_t1", "total_t1"], value_vars=["add_value_t1", "remove_value_t1"],
    var_name="Type", value_name="Value")

    chart_values_type = alt.Chart(df_melt_type).mark_bar().encode(
        y=alt.Y("error_t1:N", sort=list(df_val_type_top["error_t1"]), axis=alt.Axis(title=None, labelLimit=200, labelAngle=0)),
        x=alt.X("Value:Q", stack="zero", axis=alt.Axis(title=None)),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["add_value_t1", "remove_value_t1"], range=["#ff4b4b", "#0068c9"]), legend=None),
        tooltip=["error_t1", "Type", "Value"]
    ).properties(
        height=240,
        width="container"
    )

    st.altair_chart(chart_values_type, use_container_width=True)

def show_date_filters():
    """Display date filters and update data when dates change"""
    st.write("Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start",
            key="start_date",
            format="MM/DD/YYYY"
        )
    with col2:
        end_date = st.date_input(
            "End",
            key="end_date",
            format="MM/DD/YYYY"
        )

def show_totals(filtered_df_t1):
    """Display totals section"""
    st.session_state['added_value'] = filtered_df_t1["add_value_t1"].sum()
    st.session_state['saved_value'] = filtered_df_t1["remove_value_t1"].sum()
    st.session_state['total_value'] = filtered_df_t1["total_t1"].sum()
    
    added_value = st.session_state['added_value']
    saved_value = st.session_state['saved_value']
    total_value = st.session_state['total_value']
    
    color_add = "#ff4b4b"
    color_save = "#0068c9"

    st.metric("Total Reallocated Value", value=f"${total_value:,.2f}")
    custom_divider("1px", "0 0")
    st_custom_metric_money("Added Value", added_value, color_add)
    custom_divider("1px", "0 0")
    col1, col2 = st.columns([1, 1], gap='small')
    with col1:
        st_custom_metric_money("Saved Value", saved_value, color_save)
    with col2:
        st.metric(
            "Total Errors",
            value=f"{st.session_state['total_errors']}",
            help="Total count of errors in the selected period and filters"
        )

def show_by_month_dashboard(filtered_df_t1, teams, all_errors):
    """Visão alternativa: estrutura inspirada na tela principal, mas agrupando por mês."""
    filtered_df_t1 = filtered_df_t1.copy()
    filtered_df_t1["month"] = filtered_df_t1["date_t1"].dt.to_period("M").astype(str)

    # Primeira linha: filtros, gráfico, totais
    filters_teams, graph_bymonth, totals_1 = st.columns([1, 3, 1], gap='small', border=True)
    with filters_teams:
        st.write("Teams")
        with st.container(height=250, border=False):
            if teams:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Select all", key="select_all_teams_btn_month"):
                        for team in teams:
                            st.session_state.teams_state[team] = True
                            st.session_state[f"team_{team}"] = True
                        st.session_state.select_all_teams = True
                        st.rerun()
                with col_btn2:
                    if st.button("Unselect all", key="unselect_all_teams_btn_month"):
                        for team in teams:
                            st.session_state.teams_state[team] = False
                            st.session_state[f"team_{team}"] = False
                        st.session_state.select_all_teams = False
                        st.rerun()
                for team in teams:
                    key = f"team_{team}"
                    checked = st.checkbox(team, key=key,
                        on_change=lambda t=team: st.session_state.teams_state.update({t: st.session_state[f"team_{t}"]}))
                    st.session_state.teams_state[team] = checked
                st.session_state.select_all_teams = all(st.session_state.teams_state.values())
            else:
                st.info("No teams available.")

    with graph_bymonth:
        st.write("Errors by Month")
        month_counts = filtered_df_t1.groupby("month").size().reset_index(name="Count")
        chart = alt.Chart(month_counts).mark_bar().encode(
            x=alt.X("month:N", sort=None, axis=alt.Axis(title="Month")),
            y=alt.Y("Count:Q", axis=alt.Axis(title="Errors")),
            tooltip=["month", "Count"]
        ).properties(
            width="container",
            height=250
        )
        st.altair_chart(chart, use_container_width=True)

    with totals_1:
        show_date_filters()
        st.divider()
        st.link_button(":material/view_list: Database", f"https://docs.google.com/spreadsheets/d/{{DOCUMENT_ID}}/edit#gid={{GID_T1}}", use_container_width=True)

    # Segunda linha: filtro de erros, duas tabelas, totais
    filtered_errors, table_teams, table_types, totals_2 = st.columns([1, 1.5, 1.5, 1], gap='small', border=True)
    with filtered_errors:
        st.write("Errors")
        with st.container(height=250, border=False):
            if all_errors:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Select all", key="select_all_errors_btn_month"):
                        for error in all_errors:
                            st.session_state['checkbox_states'][error] = True
                            st.session_state[f"error_{error}"] = True
                        st.session_state.select_all_errors = True
                        st.rerun()
                with col_btn2:
                    if st.button("Unselect all", key="unselect_all_errors_btn_month"):
                        for error in all_errors:
                            st.session_state['checkbox_states'][error] = False
                            st.session_state[f"error_{error}"] = False
                        st.session_state.select_all_errors = False
                        st.rerun()
                for error in all_errors:
                    key = f"error_{error}"
                    checked = st.checkbox(str(error), key=key,
                        on_change=lambda e=error: st.session_state['checkbox_states'].update({e: st.session_state[f"error_{e}"]}))
                    st.session_state['checkbox_states'][error] = checked
                st.session_state.select_all_errors = all(st.session_state['checkbox_states'].get(error, False) for error in all_errors)
            else:
                st.info("No errors available.")

    with table_teams:
        st.write("Team Errors")
        team_counts = filtered_df_t1["team_t1"].value_counts().sort_values(ascending=False)
        team_counts_df = team_counts.reset_index()
        team_counts_df.columns = ["Team", "Qty"]
        st.dataframe(team_counts_df, use_container_width=True, hide_index=True, height=250)

    with table_types:
        st.write("Error Types")
        type_counts = filtered_df_t1["error_t1"].value_counts().sort_values(ascending=False)
        type_counts_df = type_counts.reset_index()
        type_counts_df.columns = ["Error", "Qty"]
        st.dataframe(type_counts_df, use_container_width=True, hide_index=True, height=250)

    with totals_2:
        show_totals(filtered_df_t1) 