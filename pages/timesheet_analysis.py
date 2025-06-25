import streamlit as st
import altair as alt
import pandas as pd
from datetime import datetime
from database.database_timesheet_analysis import *
from database.mongodb_utils import get_collection_data, get_user_name, get_collection_data_by_area
from utils.modal import show_manage_modal
from database.database_timesheet_analysis import load_data, filtrar_dados_timesheet
import io
import datetime as dt

# Proteção de acesso: só usuários autenticados
if not st.session_state.get('authenticated', False):
    st.warning("Você precisa estar autenticado para acessar esta página.")
    st.stop()

def show_screen(user_data):
    data = st.session_state.get('timesheet_analysis_data_cache')
    if data is None:
        st.error('Dados não carregados. Refaça o login ou recarregue a página.')
        return
    df_t1, df_t2 = data

    # Dados do MongoDB agora também do cache
    action_plans = st.session_state.get('timesheet_action_plans_cache')
    monthly_highlights = st.session_state.get('timesheet_monthly_highlights_cache')
    monthly_opportunities = st.session_state.get('timesheet_monthly_opportunities_cache')
    if action_plans is None or monthly_highlights is None or monthly_opportunities is None:
        st.error('Dados de destaques, oportunidades ou planos de ação não carregados. Refaça o login ou recarregue a página.')
        return
    # Carregar dados do MongoDB filtrados por área 'timesheet'
    action_plans = get_collection_data_by_area('action_plans', area_filter='timesheet')
    monthly_highlights = get_collection_data_by_area('monthly_highlights', include_id=True, area_filter='timesheet')
    monthly_opportunities = get_collection_data_by_area('monthly_opportunities', include_id=True, area_filter='timesheet')

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

    # Inicialização dos filtros de ano e mês (garantir antes de qualquer widget)
    # Get available years after filtering
    available_years = sorted(df_t1["year"].dropna().unique().astype(int))
    if not available_years:
        st.info("Nenhum dado disponível para os filtros selecionados.")
        return
    if 'selected_year_timesheet_analysis2' not in st.session_state or st.session_state.selected_year_timesheet_analysis2 not in available_years:
        current_year = datetime.now().year
        st.session_state.selected_year_timesheet_analysis2 = (
            current_year if current_year in available_years 
            else available_years[-1] if available_years 
            else None
        )
    selected_year = st.session_state['selected_year_timesheet_analysis2']
    filtered_year = df_t1[df_t1["year"] == selected_year]
    available_months = sorted(filtered_year["month"].dropna().unique().astype(int))
    if 'selected_month_timesheet_analysis2' not in st.session_state or (
        st.session_state['selected_month_timesheet_analysis2'] not in available_months
        and st.session_state['selected_month_timesheet_analysis2'] != 0
    ):
        st.session_state['selected_month_timesheet_analysis2'] = 0  # Complete Year como padrão
    selected_month = st.session_state['selected_month_timesheet_analysis2']

    # Filtros horizontalizados no topo
    with st.container(border=True):
        col0, col1, col2, col3 = st.columns([1.3, 1.7, 3.5, 3.5], gap="small", vertical_alignment="center")
        with col0:
            st.subheader(":material/filter_list: Filters")
        with col1:
            st.pills(
                "Corporation",
                options=corporations,
                key="corporation_select_timesheet_analysis2",
                help="Select the corporation"
            )
        with col2:
            st.multiselect(
                "Teams",
                options=teams,
                key="teams_multiselect_timesheet_analysis2"
            )
        with col3:
            st.multiselect(
                "Errors",
                options=all_errors,
                key="errors_multiselect_timesheet_analysis2"
            )

    # Apply filters
    selected_corporation = st.session_state.corporation_select_timesheet_analysis2
    selected_teams = st.session_state.teams_multiselect_timesheet_analysis2
    selected_errors = st.session_state.errors_multiselect_timesheet_analysis2
    
    # Filtrar dados pelo ano e mês selecionados
    if selected_month == 0:
        filtered_month = filtered_year
    else:
        filtered_month = filtered_year[filtered_year["month"] == selected_month]

    # Definir os filtros de ano e mês selecionados
    selected_year = st.session_state['selected_year_timesheet_analysis2']
    selected_month = st.session_state['selected_month_timesheet_analysis2']

    # Filtrar dados do MongoDB conforme ano/mês selecionados
    if selected_month == 0:
        filtered_action_plans = [p for p in action_plans if hasattr(p.get('created_at', None), 'year') and p['created_at'].year == selected_year]
        filtered_highlights = [h for h in monthly_highlights if h.get('year') == selected_year]
        filtered_opportunities = [o for o in monthly_opportunities if o.get('year') == selected_year]
    else:
        filtered_action_plans = [p for p in action_plans if hasattr(p.get('created_at', None), 'year') and p['created_at'].year == selected_year and p['created_at'].month == selected_month]
        filtered_highlights = [h for h in monthly_highlights if h.get('year') == selected_year and h.get('month') == selected_month]
        filtered_opportunities = [o for o in monthly_opportunities if o.get('year') == selected_year and o.get('month') == selected_month]

    # Duas colunas principais para dados
    col_dados, col_lateral = st.columns([7, 3], gap="small")
    with col_dados:
        with st.container(border=True):
            col_header, col_empty, col_btn = st.columns([3, 1, 1], vertical_alignment="center")
            with col_header:
                st.header(":material/calendar_month: Analysis by Month")
            with col_empty:
                st.empty()
            with col_btn:
                # Permitir acesso para usuários com role timesheet_admin
                if "timesheet_admin" in user_data.get("roles", []):
                    if st.button(":material/database: Manage Data", key="manage_data_btn", type="secondary"):
                        print("DEBUG: Botão Manage Data clicado em timesheet_analysis")
                        st.session_state['show_manage_modal'] = True
                        st.session_state['modal_page'] = 'timesheet_analysis'
            # Controles de Year e Month na mesma linha (acima do gráfico)
            col_year, col_month = st.columns([1, 3])
            with col_year:
                st.selectbox(
                    "Year",
                    options=available_years,
                    key="selected_year_timesheet_analysis2"
                )
            with col_month:
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
            # Gráfico, métricas, tabelas Teams/Errors
            # NOVO GRÁFICO DE CONTAGEM
            if st.session_state['selected_month_timesheet_analysis2'] == 0:
                chart_data = filtered_year.groupby("month").size().reset_index(name="event_count")
                chart_data = chart_data.sort_values("month")
                months_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                chart_data["month_name"] = chart_data["month"].apply(lambda x: months_labels[x-1] if 1 <= x <= 12 else str(x))
                base = alt.Chart(chart_data).encode(
                    x=alt.X('month:O', axis=alt.Axis(title='Month', values=list(range(1,13)), labelExpr='datum.value')),
                    y=alt.Y('event_count:Q', axis=alt.Axis(title='Error Count'))
                )
                line = base.mark_line(color="#0068c9")
                points = base.mark_point(filled=True, size=80, color="#0068c9").encode(
                    tooltip=[
                        alt.Tooltip('month:O', title='Month'),
                        alt.Tooltip('event_count:Q', title='Error Count')
                    ]
                )
                chart = alt.layer(line, points)
                chart = chart.configure_legend(
                    orient='top',
                    title=None,
                    labelFontSize=12
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                chart_data = filtered_month.groupby(filtered_month["date_t1"].dt.day).size().reset_index(name="event_count")
                chart_data = chart_data.rename(columns={"date_t1": "day"})
                chart_data = chart_data.sort_values("day")
                base = alt.Chart(chart_data).encode(
                    x=alt.X('day:O', axis=alt.Axis(title='Day')),
                    y=alt.Y('event_count:Q', axis=alt.Axis(title='Error Count'))
                )
                line = base.mark_line(color="#0068c9")
                points = base.mark_point(filled=True, size=80, color="#0068c9").encode(
                    tooltip=[
                        alt.Tooltip('day:O', title='Day'),
                        alt.Tooltip('event_count:Q', title='Error Count')
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
            st.markdown("### :material/groups: Teams")
            team_df = filtered_month.groupby("team_t1").agg(
                Error_Count=("team_t1", "count"),
                Added_Value=("add_value_t1", "sum"),
                Removed_Value=("remove_value_t1", "sum")
            ).reset_index().sort_values("Error_Count", ascending=False)
            st.dataframe(team_df, use_container_width=True, hide_index=True)
            st.markdown("### :material/close: Errors")
            error_df = filtered_month.groupby("error_t1").agg(
                Count=("error_t1", "count"),
                Added_Value=("add_value_t1", "sum"),
                Removed_Value=("remove_value_t1", "sum")
            ).reset_index().sort_values("Count", ascending=False)
            st.dataframe(error_df, use_container_width=True, hide_index=True)

            st.warning("É necessário adicionar o controle de erros internos do Office para o timesheet como um novo st.dataframe.")

    with col_lateral:
        with st.container(border=True):
            # 1. Monthly Highlights
            st.subheader(":material/rocket_launch: Monthly Highlights")
            # Agrupar highlights por (month, year)
            highlights_by_month = {}
            for h in filtered_highlights:
                key = (h.get('month', ''), h.get('year', ''))
                if key not in highlights_by_month:
                    highlights_by_month[key] = []
                highlights_by_month[key].append(h)
            if highlights_by_month:
                for (month, year), highlights_list in sorted(highlights_by_month.items(), key=lambda x: (x[1][0].get('year', 0), x[1][0].get('month', 0))):
                    # Buscar o nome do usuário responsável pelo primeiro highlight da lista
                    user_name = "Usuário não encontrado"
                    if highlights_list and 'user_id' in highlights_list[0]:
                        user_name = get_user_name(highlights_list[0]['user_id'])
                    
                    with st.expander(f"{user_name} • {month}/{year}"):
                        for highlight in highlights_list:
                            col_pos, col_neg = st.columns(2)
                            with col_pos:
                                st.markdown(":material/thumb_up:  **Positives:**")
                                for p in highlight.get('positive', []):
                                    if p.get('title', '').startswith('**'):
                                        st.markdown(f":blue[:material/star: {p.get('title', '')}]")
                                    else:
                                        st.markdown(f":blue[:material/fiber_manual_record:] {p.get('title', '')}")
                            with col_neg:
                                st.markdown(":material/thumb_down:  **Negatives:**")
                                for n in highlight.get('negative', []):
                                    if n.get('title', '').startswith('**'):
                                        st.markdown(f":red[:material/star: {n.get('title', '')}]")
                                    else:
                                        st.markdown(f":red[:material/fiber_manual_record:] {n.get('title', '')}")
            else:
                st.info("Nenhum destaque mensal encontrado.")

            st.divider()
            # 2. Opportunities
            st.subheader(":material/emoji_objects: Opportunities")
            # Agrupar opportunities por (month, year)
            opportunities_by_month = {}
            for o in filtered_opportunities:
                key = (o.get('month', ''), o.get('year', ''))
                if key not in opportunities_by_month:
                    opportunities_by_month[key] = []
                opportunities_by_month[key].append(o)
            if opportunities_by_month:
                for (month, year), opp_list in sorted(opportunities_by_month.items(), key=lambda x: (x[1][0].get('year', 0), x[1][0].get('month', 0))):
                    # Buscar o nome do usuário responsável pela primeira opportunity da lista
                    user_name = "Usuário não encontrado"
                    if opp_list and 'user_id' in opp_list[0]:
                        user_name = get_user_name(opp_list[0]['user_id'])
                    
                    with st.expander(f"{user_name} • {month}/{year}"):
                        opp_blocks = []
                        for opp in opp_list:
                            for o in opp.get('opportunity_list', []):
                                opp_blocks.append(o)
                        for idx, o in enumerate(opp_blocks):
                            if idx > 0:
                                st.divider()
                            st.markdown(f"##### {o.get('title', '')}")
                            st.markdown(":material/priority_high:  **Challenges:**")
                            for c in o.get('challenges', []):
                                st.markdown(f"- {c}")
                            st.markdown(":material/trending_up:  **Improvements:**")
                            for i in o.get('improvements', []):
                                st.markdown(f"- {i}")
            else:
                st.info("Nenhuma oportunidade encontrada.")

            st.divider()
            # 3. Action Plans
            st.subheader(":material/map: Action Plans")
            if filtered_action_plans:
                for plan in filtered_action_plans:
                    with st.expander(f"{plan.get('title', '')}  |  **{plan.get('description', '')}**"):
                        created_at = plan.get('created_at', '')
                        if hasattr(created_at, 'strftime'):
                            created_at = created_at.strftime('%m/%d/%Y')
                        subplans = plan.get('subplans', [])
                        if subplans:
                            for idx, sub in enumerate(subplans):
                                if idx > 0:
                                    st.divider()
                                sub_title = sub.get('title', '')
                                sub_reason = sub.get('reason', '')
                                start = sub.get('start_date', '')
                                end = sub.get('end_date', '')
                                responsible = sub.get('responsible', '')
                                if hasattr(start, 'strftime'):
                                    start = start.strftime('%m/%d')
                                if hasattr(end, 'strftime'):
                                    end = end.strftime('%m/%d')
                                st.markdown(f"##### {sub_title}")
                                st.markdown(f"{sub_reason}")
                                actions = sub.get('actions', [])
                                if actions:
                                    for idx2, a in enumerate(actions, 1):
                                        step_title = a.get('title', '')
                                        responsible = a.get('responsible', '')
                                        due_date = a.get('due_date', '')
                                        if hasattr(due_date, 'strftime'):
                                            due_date = due_date.strftime('%m/%d')
                                        status = a.get('status', '')
                                        st.markdown(f"###### {idx2}- {step_title}")
                                        step_df = pd.DataFrame([
                                            {
                                                'Responsible': responsible,
                                                'Due Date': due_date,
                                                'Status': status
                                            }
                                        ])
                                        st.dataframe(step_df, use_container_width=True, hide_index=True)
                                else:
                                    st.info("Nenhuma etapa cadastrada.")
                        else:
                            st.info("Nenhum subplano cadastrado.")
                        # Botão de download Excel no final
                        st.divider()
                        def format_date_only(val):
                            if isinstance(val, (dt.datetime, dt.date)):
                                return val.strftime('%m/%d/%Y')
                            if isinstance(val, str):
                                try:
                                    return pd.to_datetime(val).strftime('%m/%d/%Y')
                                except:
                                    return val
                            return val
                        plan_data = {
                            'Title': plan.get('title', ''),
                            'Description': plan.get('description', ''),
                            'Created At': format_date_only(plan.get('created_at', '')),
                            'Area': plan.get('area', ''),
                        }
                        subplans_data = []
                        actions_data = []
                        for sub in subplans:
                            sub_dict = {
                                'Subplan Title': sub.get('title', ''),
                                'Reason': sub.get('reason', ''),
                                'Start Date': format_date_only(sub.get('start_date', '')),
                                'End Date': format_date_only(sub.get('end_date', '')),
                            }
                            subplans_data.append(sub_dict)
                            for a in sub.get('actions', []):
                                actions_data.append({
                                    'Subplan Title': sub.get('title', ''),
                                    'Action Title': a.get('title', ''),
                                    'Status': a.get('status', ''),
                                    'Due Date': format_date_only(a.get('due_date', '')),
                                    'Responsible': a.get('responsible', ''),
                                })
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            pd.DataFrame([plan_data]).to_excel(writer, index=False, sheet_name='Plan')
                            pd.DataFrame(subplans_data).to_excel(writer, index=False, sheet_name='Subplans')
                            pd.DataFrame(actions_data).to_excel(writer, index=False, sheet_name='Actions')
                        output.seek(0)
                        st.download_button(
                            label=':material/file_save:',
                            data=output,
                            file_name=f"action_plan_{plan.get('title','plan')}.xlsx",
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            use_container_width=True,
                            help='Exportar para Excel'
                        )
            else:
                st.info("Nenhum plano de ação encontrado.")