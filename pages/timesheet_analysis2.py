import streamlit as st
import altair as alt
import pandas as pd
from datetime import datetime
from database.database_timesheet_analysis import *
from database.mongodb_utils import get_collection_data

# Proteção de acesso: só usuários autenticados
if not st.session_state.get('authenticated', False):
    st.warning("Você precisa estar autenticado para acessar esta página.")
    st.stop()

def show_screen(user_data):
    # Carregar dados do MongoDB
    action_plans = get_collection_data('action_plans')
    monthly_highlights = get_collection_data('monthly_highlights')
    monthly_opportunities = get_collection_data('monthly_opportunities')

    # Carregar dados
    df_t1, df_t2 = load_data()
    if df_t1.empty or df_t2.empty:
        st.error("Erro ao carregar dados. Tente novamente mais tarde.")
        return
    
    # Process data
    df_t1.columns = df_t1.columns.str.strip()
    df_t1["date_t1"] = pd.to_datetime(df_t1["date_t1"], errors="coerce")
    df_t1 = df_t1.dropna(subset=["date_t1"])  # Remove linhas com datas inválidas
    df_t1["month"] = df_t1["date_t1"].dt.month.astype(int)
    df_t1["year"] = df_t1["date_t1"].dt.year.astype(int)
    
    # Get unique values
    teams = sorted(df_t1["team_t1"].dropna().unique())
    all_errors = sorted(df_t1["error_t1"].dropna().unique())
    corporations = ["All"] + sorted(df_t1["corporation_t1"].dropna().astype(str).unique())

    # Initialize session state with basic values only
    if 'corporation_select_timesheet_analysis2' not in st.session_state:
        st.session_state.corporation_select_timesheet_analysis2 = "All"
    if 'teams_multiselect_timesheet_analysis2' not in st.session_state:
        st.session_state.teams_multiselect_timesheet_analysis2 = []  # Começa vazio
    if 'errors_multiselect_timesheet_analysis2' not in st.session_state:
        st.session_state.errors_multiselect_timesheet_analysis2 = []  # Começa vazio

    # Layout principal
    col_filtros, col_dados, col_vazia = st.columns([10,25,15], gap="small")
    
    with col_filtros:
        with st.container(border=True):
            st.subheader("Filters")
            
            # Corporation
            st.pills(
                "Corporation",
                options=corporations,
                key="corporation_select_timesheet_analysis2",
                help="Select the corporation"
            )
            
            # Teams
            st.multiselect(
                "Teams",
                options=teams,
                key="teams_multiselect_timesheet_analysis2"
            )
            
            # Errors
            st.multiselect(
                "Errors",
                options=all_errors,
                key="errors_multiselect_timesheet_analysis2"
            )
    
    # Apply filters
    filtered = df_t1.copy()
    selected_corporation = st.session_state.corporation_select_timesheet_analysis2
    selected_teams = st.session_state.teams_multiselect_timesheet_analysis2
    selected_errors = st.session_state.errors_multiselect_timesheet_analysis2
    
    if selected_corporation and selected_corporation != "All":
        filtered = filtered[filtered["corporation_t1"] == selected_corporation]
    if selected_teams:
        filtered = filtered[filtered["team_t1"].isin(selected_teams)]
    if selected_errors:
        filtered = filtered[filtered["error_t1"].isin(selected_errors)]
    
    # Get available years after filtering
    available_years = sorted(filtered["year"].dropna().unique().astype(int))
    
    if not available_years:
        st.info("Nenhum dado disponível para os filtros selecionados.")
        return

    # Now initialize year selection after we have available_years
    if 'selected_year_timesheet_analysis2' not in st.session_state or st.session_state.selected_year_timesheet_analysis2 not in available_years:
        current_year = datetime.now().year
        st.session_state.selected_year_timesheet_analysis2 = (
            current_year if current_year in available_years 
            else available_years[-1] if available_years 
            else None
        )
    
    # Filtrar dados do ano selecionado para uso posterior
    filtered_year = filtered[filtered["year"] == st.session_state['selected_year_timesheet_analysis2']]
    available_months = sorted(filtered_year["month"].dropna().unique().astype(int))

    # Inicialização do filtro de mês
    if 'selected_month_timesheet_analysis2' not in st.session_state or (
        st.session_state['selected_month_timesheet_analysis2'] not in available_months
        and st.session_state['selected_month_timesheet_analysis2'] != 0
    ):
        st.session_state['selected_month_timesheet_analysis2'] = 0  # Complete Year como padrão

    # Filtrar dados pelo ano e mês selecionados
    if st.session_state['selected_month_timesheet_analysis2'] == 0:
        filtered_month = filtered_year
    else:
        filtered_month = filtered_year[filtered_year["month"] == st.session_state['selected_month_timesheet_analysis2']]

    with col_dados:
        with st.container(border=True):
            st.subheader("Analysis by Month")
            # Controles de Year e Month na mesma linha
            col_year, col_month = st.columns([1, 3])
            with col_year:
                st.selectbox(
                    "Year",
                    options=available_years,
                    key="selected_year_timesheet_analysis2"
                )
            with col_month:
                # st.pills para os meses
                months_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                months_options = available_months.copy()
                months_labels_full = [months_labels[m-1] for m in months_options]
                months_options_with_all = [0] + months_options  # 0 será 'Complete Year'
                months_labels_with_all = ["Complete Year"] + months_labels_full
                st.pills(
                    label="Month",
                    options=months_options_with_all,
                    format_func=lambda x: months_labels_with_all[months_options_with_all.index(x)],
                    key="selected_month_timesheet_analysis2"
                )

            # Gráfico de linha (mostra apenas os meses filtrados)
            chart_data = filtered_month.groupby("month").agg({
                "add_value_t1": "sum",
                "remove_value_t1": "sum"
            }).reset_index()
            chart_data = chart_data.sort_values("month")
            # Adicionar coluna de nome do Month para tooltip
            months_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            chart_data["month_name"] = chart_data["month"].apply(lambda x: months_labels[x-1] if 1 <= x <= 12 else str(x))
            # Adicionar coluna de contagem de erros (linhas)
            chart_data["error_count"] = filtered_month.groupby("month")["team_t1"].count().reindex(chart_data["month"]).values

            # Transformar chart_data para formato long
            chart_data_long = pd.melt(
                chart_data,
                id_vars=["month", "month_name", "error_count"],
                value_vars=["add_value_t1", "remove_value_t1"],
                var_name="Type",
                value_name="Value"
            )
            chart_data_long["Type"] = chart_data_long["Type"].map({
                "add_value_t1": "Added Value",
                "remove_value_t1": "Removed Value"
            })

            base = alt.Chart(chart_data_long).encode(
                x=alt.X('month:O', axis=alt.Axis(title='Month', values=list(range(1,13)), labelExpr='datum.value')),
                color=alt.Color('Type:N', scale=alt.Scale(domain=["Added Value", "Removed Value"], range=["#0068c9", "#ff4b4b"]), legend=alt.Legend(title="Type"))
            )
            line = base.mark_line().encode(
                y=alt.Y('Value:Q', axis=alt.Axis(title='Value'))
            )
            points = base.mark_point(filled=True, size=80).encode(
                y='Value:Q',
                tooltip=[
                    alt.Tooltip('month:O', title='Month'),
                    alt.Tooltip('Type:N', title='Type'),
                    alt.Tooltip('Value:Q', title='Value', format=",.2f"),
                    alt.Tooltip('error_count:Q', title='Error Count')
                ]
            )
            chart = alt.layer(line, points)
            chart = chart.configure_legend(
                orient='top',
                title=None,
                labelFontSize=12
            )
            st.altair_chart(chart, use_container_width=True)

            # MÉTRICAS PERSONALIZADAS USANDO FILTERED_MONTH
            total_errors = int(filtered_month.shape[0])
            total_added = filtered_month['add_value_t1'].sum()
            total_removed = filtered_month['remove_value_t1'].sum()
            col1, col2, col3 = st.columns([1, 2, 2], gap="small")
            with col1:
                st.markdown(f"<div style='color:#222;font-size:2em;font-weight:400;'>{total_errors}</div>", unsafe_allow_html=True)
                st.caption("Total Errors")
            with col2:
                st.markdown(f"<div style='color:#0068c9;font-size:2em;font-weight:400;'>+${total_added:,.2f}</div>", unsafe_allow_html=True)
                st.caption("Added Value")
            with col3:
                st.markdown(f"<div style='color:#ff4b4b;font-size:2em;font-weight:400;'>-${total_removed:,.2f}</div>", unsafe_allow_html=True)
                st.caption("Removed Value")

            # Dataframes filtrados pelo mês
            st.markdown("### Teams")
            team_df = filtered_month.groupby("team_t1").agg(
                Error_Count=("team_t1", "count"),
                Added_Value=("add_value_t1", "sum"),
                Removed_Value=("remove_value_t1", "sum")
            ).reset_index().sort_values("Error_Count", ascending=False)
            st.dataframe(team_df, use_container_width=True, hide_index=True)
            st.markdown("### Errors")
            error_df = filtered_month.groupby("error_t1").agg(
                Count=("error_t1", "count"),
                Added_Value=("add_value_t1", "sum"),
                Removed_Value=("remove_value_t1", "sum")
            ).reset_index().sort_values("Count", ascending=False)
            st.dataframe(error_df, use_container_width=True, hide_index=True)
    # Terceira coluna vazia
    with col_vazia:
        with st.container(border=True):
            st.subheader("Action Plans")
            # Filtros de ano e mês selecionados
            selected_year = st.session_state['selected_year_timesheet_analysis2']
            selected_month = st.session_state['selected_month_timesheet_analysis2']

            # Filtrar dados do MongoDB conforme ano/mês
            if selected_month == 0:
                filtered_action_plans = [p for p in action_plans if hasattr(p.get('created_at', None), 'year') and p['created_at'].year == selected_year]
                filtered_highlights = [h for h in monthly_highlights if h.get('year') == selected_year]
                filtered_opportunities = [o for o in monthly_opportunities if o.get('year') == selected_year]
            else:
                filtered_action_plans = [p for p in action_plans if hasattr(p.get('created_at', None), 'year') and p['created_at'].year == selected_year and p['created_at'].month == selected_month]
                filtered_highlights = [h for h in monthly_highlights if h.get('year') == selected_year and h.get('month') == selected_month]
                filtered_opportunities = [o for o in monthly_opportunities if o.get('year') == selected_year and o.get('month') == selected_month]

            if filtered_action_plans:
                for plan in filtered_action_plans:
                    st.markdown(f"**{plan.get('title', '')}**  \n{plan.get('description', '')}")
                    created_at = plan.get('created_at', '')
                    if hasattr(created_at, 'strftime'):
                        created_at = created_at.strftime('%d/%m/%Y')
                    st.caption(f"Criado em: {created_at}")
                    for sub in plan.get('subplans', []):
                        sub_title = sub.get('title', '')
                        sub_reason = sub.get('reason', '')
                        start = sub.get('start_date', '')
                        end = sub.get('end_date', '')
                        if hasattr(start, 'strftime'):
                            start = start.strftime('%d/%m')
                        if hasattr(end, 'strftime'):
                            end = end.strftime('%d/%m')
                        with st.expander(f"Subplano: {sub_title} ({start} - {end})"):
                            st.markdown(f"Motivo: {sub_reason}")
                            for action in sub.get('actions', []):
                                status_icon = '✅' if action.get('status', '') == 'concluído' else '⏳'
                                due = action.get('due_date', '')
                                if hasattr(due, 'strftime'):
                                    due = due.strftime('%d/%m')
                                st.markdown(f"- {status_icon} **{action.get('title', '')}** (Vencimento: {due})")
            else:
                st.info("Nenhum plano de ação encontrado.")

            st.divider()
            st.subheader("Monthly Highlights")
            if filtered_highlights:
                for highlight in filtered_highlights:
                    st.markdown(f"**{highlight.get('month', '')}/{highlight.get('year', '')}**")
                    col_pos, col_neg = st.columns(2)
                    with col_pos:
                        st.markdown("**Positivos:**")
                        for p in highlight.get('positive', []):
                            st.markdown(f"- 👍 {p.get('title', '')}")
                    with col_neg:
                        st.markdown("**Negativos:**")
                        for n in highlight.get('negative', []):
                            st.markdown(f"- 👎 {n.get('title', '')}")
            else:
                st.info("Nenhum destaque mensal encontrado.")

            st.divider()
            st.subheader("Opportunities")
            if filtered_opportunities:
                for opp in filtered_opportunities:
                    st.markdown(f"**{opp.get('month', '')}/{opp.get('year', '')}**")
                    for o in opp.get('opportunity_list', []):
                        with st.expander(f"Oportunidade {o.get('id', '')}"):
                            st.markdown("**Desafios:**")
                            for c in o.get('challenges', []):
                                st.markdown(f"- ⚠️ {c}")
                            st.markdown("**Melhorias:**")
                            for i in o.get('improvements', []):
                                st.markdown(f"- 💡 {i}")
            else:
                st.info("Nenhuma oportunidade encontrada.")