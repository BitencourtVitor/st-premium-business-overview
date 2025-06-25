import streamlit as st
import altair as alt
import pandas as pd
from datetime import datetime
from database.database_accounting_indicators import load_data_accounting_indicators, filtrar_dados_accounting
from database.mongodb_utils import get_collection_data_by_area, get_user_name
from utils.modal import show_manage_modal
import io
import datetime as dt

# Proteção de acesso: só usuários autenticados
if not st.session_state.get('authenticated', False):
    st.warning("Você precisa estar autenticado para acessar esta página.")
    st.stop()

def show_screen(user_data):
    df = st.session_state.get('accounting_indicators_data_cache')
    if df is None:
        st.error('Dados não carregados. Refaça o login ou recarregue a página.')
        return
    # Conversão explícita dos tipos necessários para o gráfico funcionar
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Open balance"] = (
        df["Open balance"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("nan", None)
        .astype(float)
    )
    df = df.dropna(subset=["Date"])
    df["month"] = df["Date"].dt.month.astype(int)
    df["year"] = df["Date"].dt.year.astype(int)
    # Filtros
    aging_intervals = ["All"] + sorted(df["Aging Intervals"].dropna().unique())
    categories = sorted(df["Category"].dropna().unique())
    seg_options = ["All", "Receivables"]
    if "accounting_segmented_control" not in st.session_state:
        st.session_state.accounting_segmented_control = "All"
    if "accounting_aging_pill" not in st.session_state:
        st.session_state.accounting_aging_pill = aging_intervals[0] if aging_intervals else None
    if "accounting_category_multiselect" not in st.session_state:
        st.session_state.accounting_category_multiselect = []
    selected_type = st.session_state.accounting_segmented_control
    selected_aging = st.session_state.accounting_aging_pill
    selected_categories = st.session_state.accounting_category_multiselect
    # Aplicar filtros manualmente (como era antes)
    filtered = df.copy()
    if selected_type == "Receivables":
        filtered = filtered[filtered["Transaction type"] == "Invoice"]
    if selected_aging and selected_aging != "All":
        filtered = filtered[filtered["Aging Intervals"] == selected_aging]
    if selected_categories:
        filtered = filtered[filtered["Category"].isin(selected_categories)]
    # Filtros de ano e mês
    available_years = sorted(filtered["year"].dropna().unique().astype(int))
    if not available_years:
        st.info("Nenhum dado disponível para os filtros selecionados.")
        return
    if 'selected_year_accounting_indicators' not in st.session_state or st.session_state.selected_year_accounting_indicators not in available_years:
        current_year = datetime.now().year
        st.session_state.selected_year_accounting_indicators = (
            current_year if current_year in available_years 
            else available_years[-1] if available_years 
            else None
        )
    filtered_year = filtered[filtered["year"] == st.session_state['selected_year_accounting_indicators']]
    available_months = sorted(filtered_year["month"].dropna().unique().astype(int))
    if 'selected_month_accounting_indicators' not in st.session_state or (
        st.session_state['selected_month_accounting_indicators'] not in available_months
        and st.session_state['selected_month_accounting_indicators'] != 0
    ):
        st.session_state['selected_month_accounting_indicators'] = 0
    if st.session_state['selected_month_accounting_indicators'] == 0:
        filtered_month = filtered_year
    else:
        filtered_month = filtered_year[filtered_year["month"] == st.session_state['selected_month_accounting_indicators']]
    # Definir ano/mês selecionados
    selected_year = st.session_state['selected_year_accounting_indicators']
    selected_month = st.session_state['selected_month_accounting_indicators']
    # --- USAR DADOS DO MONGODB PARA OS CARDS LATERAIS ---
    action_plans = get_collection_data_by_area('action_plans', area_filter='accounting')
    monthly_highlights = st.session_state.get('accounting_monthly_highlights_cache', [])
    monthly_opportunities = st.session_state.get('accounting_monthly_opportunities_cache', [])
    # Filtrar conforme ano/mês selecionados
    if selected_month == 0:
        filtered_action_plans = [p for p in action_plans if hasattr(p.get('created_at', None), 'year') and p['created_at'].year == selected_year]
        filtered_highlights = [h for h in monthly_highlights if h.get('year') == selected_year]
        filtered_opportunities = [o for o in monthly_opportunities if o.get('year') == selected_year]
    else:
        filtered_action_plans = [p for p in action_plans if hasattr(p.get('created_at', None), 'year') and p['created_at'].year == selected_year and p['created_at'].month == selected_month]
        filtered_highlights = [h for h in monthly_highlights if h.get('year') == selected_year and h.get('month') == selected_month]
        filtered_opportunities = [o for o in monthly_opportunities if o.get('year') == selected_year and o.get('month') == selected_month]
    # Filtros horizontalizados no topo (container sozinho, ponta a ponta)
    with st.container(border=True):
        col0, col1, col2, col3 = st.columns([1.3, 2, 3, 3], gap="small", vertical_alignment="center")
        with col0:
            st.subheader(":material/filter_list: Filters")
        with col1:
            st.segmented_control(
                "Type",
                options=seg_options,
                key="accounting_segmented_control",
                help="Select Receivables"
            )
        with col2:
            st.pills(
                "Aging Interval",
                options=aging_intervals,
                key="accounting_aging_pill"
            )
        with col3:
            st.multiselect(
                "Category",
                options=categories,
                key="accounting_category_multiselect"
            )

    # Agora, abaixo, as duas colunas principais
    col_dados, col_lateral = st.columns([7, 3], gap="small")
    with col_dados:
        with st.container(border=True):
            col_header, col_empty, col_btn = st.columns([3, 1, 1], vertical_alignment="center")
            with col_header:
                st.header(":material/calendar_month: Analysis by Month")
            with col_empty:
                st.empty()
            with col_btn:
                if "accounting_admin" in user_data.get("roles", []):
                    if st.button(":material/database: Manage Data", key="manage_data_btn_accounting", type="secondary"):
                        st.session_state['show_manage_modal'] = True
                        st.session_state['modal_page'] = 'accounting_indicators'

            # Controles de Year e Month na mesma linha (acima do gráfico)
            col_year, col_month = st.columns([1, 3])
            with col_year:
                st.selectbox(
                    "Year",
                    options=available_years,
                    key="selected_year_accounting_indicators"
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
                    key="selected_month_accounting_indicators"
                )

            # GRÁFICO (após filtros de ano/mês)
            selected_type = st.session_state.accounting_segmented_control
            selected_aging = st.session_state.accounting_aging_pill
            selected_month = st.session_state['selected_month_accounting_indicators']
            aging_interval_is_specific = selected_aging and selected_aging != "All"

            if selected_month == 0:
                # Ano completo: fechamento mensal
                last_days = filtered_year.groupby('month')['Date'].max().reset_index()
                merged = filtered_year.merge(last_days, on=['month', 'Date'])
                if aging_interval_is_specific:
                    chart_data = merged[merged["Aging Intervals"] == selected_aging].groupby(['Date'], as_index=False)['Open balance'].sum()
                    color = None
                elif selected_type == "Receivables":
                    chart_data = merged.groupby(['Date', 'Aging Intervals'], as_index=False)['Open balance'].sum()
                    color = alt.Color('Aging Intervals:N', title='Aging Intervals')
                else:
                    chart_data = merged.groupby(['Date'], as_index=False)['Open balance'].sum()
                    color = None

                # Adicionar coluna de mês abreviado para o eixo X
                chart_data['month_str'] = chart_data['Date'].dt.strftime('%b')
                base = alt.Chart(chart_data).encode(
                    x=alt.X('month_str:N', axis=alt.Axis(title='Month')),
                    y=alt.Y('Open balance:Q', axis=alt.Axis(title='Value', tickMinStep=50000)),
                    color=color if color else alt.value("#0068c9")
                )
                points_tooltip = [alt.Tooltip('month_str:N', title='Mês'), alt.Tooltip('Open balance:Q', title='Valor')]
                if color:
                    points_tooltip.insert(1, alt.Tooltip('Aging Intervals:N', title='Intervalo Etário'))
                line = base.mark_line()
                points = base.mark_point(filled=True, size=80).encode(
                    tooltip=points_tooltip
                )
                chart = alt.layer(line, points)
                chart = chart.configure_legend(orient='top', title=None, labelFontSize=12)
                st.altair_chart(chart, use_container_width=True)
            else:
                # Mês específico: valores diários
                filtered_month = filtered_month.copy()
                if aging_interval_is_specific:
                    chart_data = filtered_month[filtered_month["Aging Intervals"] == selected_aging].groupby(["Date"], as_index=False)["Open balance"].sum()
                    color = None
                elif selected_type == "Receivables":
                    chart_data = filtered_month.groupby(["Date", "Aging Intervals"], as_index=False)["Open balance"].sum()
                    color = alt.Color('Aging Intervals:N', title='Intervalo Etário')
                else:
                    chart_data = filtered_month.groupby("Date", as_index=False)["Open balance"].sum()
                    color = None

                # Adicionar coluna de dia para o eixo X
                chart_data['day_str'] = chart_data['Date'].dt.strftime('%d')
                base = alt.Chart(chart_data).encode(
                    x=alt.X('day_str:N', axis=alt.Axis(title='Day')),
                    y=alt.Y('Open balance:Q', axis=alt.Axis(title='Value', tickMinStep=50000)),
                    color=color if color else alt.value("#0068c9")
                )
                points_tooltip = [alt.Tooltip('day_str:N', title='Day'), alt.Tooltip('Open balance:Q', title='Value')]
                if color:
                    points_tooltip.insert(1, alt.Tooltip('Aging Intervals:N', title='Aging Intervals'))
                line = base.mark_line()
                points = base.mark_point(filled=True, size=80).encode(tooltip=points_tooltip)
                chart = alt.layer(line, points)
                chart = chart.configure_legend(orient='top', title=None, labelFontSize=12)
                st.altair_chart(chart, use_container_width=True)
            # Tabela: mostrar todas as colunas
            st.markdown("### :material/table: Accounting Data")
            st.dataframe(filtered_month, use_container_width=True, hide_index=True)
    # COLUNA LATERAL: Monthly Highlights, Opportunities, Action Plans
    with col_lateral:
        with st.container(border=True):
            # 1. Monthly Highlights
            st.subheader(":material/rocket_launch: Monthly Highlights")
            highlights_by_month = {}
            for h in filtered_highlights:
                key = (h.get('month', ''), h.get('year', ''))
                if key not in highlights_by_month:
                    highlights_by_month[key] = []
                highlights_by_month[key].append(h)
            if highlights_by_month:
                for (month, year), highlights_list in sorted(highlights_by_month.items(), key=lambda x: (x[1][0].get('year', 0), x[1][0].get('month', 0))):
                    user_name = "Usuário não informado"
                    if highlights_list and 'user_id' in highlights_list[0] and highlights_list[0]['user_id']:
                        try:
                            user_name = get_user_name(highlights_list[0]['user_id'])
                        except Exception as e:
                            user_name = f"Erro ao buscar usuário: {e}"
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
            opportunities_by_month = {}
            for o in filtered_opportunities:
                key = (o.get('month', ''), o.get('year', ''))
                if key not in opportunities_by_month:
                    opportunities_by_month[key] = []
                opportunities_by_month[key].append(o)
            if opportunities_by_month:
                for (month, year), opp_list in sorted(opportunities_by_month.items(), key=lambda x: (x[1][0].get('year', 0), x[1][0].get('month', 0))):
                    user_name = "Usuário não informado"
                    if opp_list and 'user_id' in opp_list[0] and opp_list[0]['user_id']:
                        try:
                            user_name = get_user_name(opp_list[0]['user_id'])
                        except Exception as e:
                            user_name = f"Erro ao buscar usuário: {e}"
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