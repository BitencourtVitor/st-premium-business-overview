import streamlit as st
import pandas as pd
from datetime import datetime, date
from database.mongodb_utils import get_collection_data_by_area, insert_document, update_document, delete_document
from bson import ObjectId

def set_active_tab(tab_name):
    st.session_state['active_modal_tab'] = tab_name

def get_active_tab(tab_names):
    return st.session_state.get('active_modal_tab', tab_names[0])

@st.dialog("Manage Data", width="large")
def _modal_dialog():
    st.write("Escolha uma aba para gerenciar.")
    tab_names = ["Monthly Highlights", "Opportunities", "Action Plans"]
    
    # Determinar qual área usar baseado na página atual
    current_page = st.session_state.get('current_page', 'timesheet_analysis')
    # Novo mapeamento expansivo de páginas para áreas
    PAGE_AREA_MAP = {
        'permit_control': 'permit',
        'accounting_indicators': 'accounting',
        'timesheet_analysis': 'timesheet',
        # Adicione aqui novas páginas e áreas conforme necessário
    }
    # Tenta mapear, senão usa o nome da página (removendo sufixos comuns)
    area_filter = PAGE_AREA_MAP.get(current_page)
    if area_filter is None:
        area_filter = current_page.replace('_analysis', '').replace('pages/', '')
    
    # Obter o user_id do usuário atual
    current_user_id = st.session_state.get('user_data', {}).get('_id')
    if not current_user_id:
        st.error("Erro: ID do usuário não encontrado. Faça login novamente.")
        return
    
    # Controle de aba ativa
    if 'active_modal_tab' not in st.session_state:
        st.session_state['active_modal_tab'] = tab_names[0]
    active_tab_idx = tab_names.index(st.session_state['active_modal_tab']) if st.session_state['active_modal_tab'] in tab_names else 0
    selected_tabs = st.tabs(tab_names)
    tab_map = dict(zip(tab_names, selected_tabs))

    # Helper for popover confirmation (precisa estar definida antes do uso)
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

    with tab_map["Monthly Highlights"]:
        set_active_tab("Monthly Highlights")
        # Buscar todos os anos disponíveis para o usuário logado
        all_highlights = get_collection_data_by_area('monthly_highlights', area_filter=area_filter, include_id=True)
        obj_user_id = ObjectId(current_user_id) if current_user_id else None
        years = sorted({h.get('year') for h in all_highlights if h.get('year') and h.get('user_id') == obj_user_id})
        if not years:
            years = [datetime.now().year]
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Year", options=years, index=years.index(datetime.now().year) if datetime.now().year in years else 0, key="highlight_year", on_change=lambda: set_active_tab("Monthly Highlights"))
        with col2:
            months_for_year = sorted({h.get('month') for h in all_highlights if h.get('year') == year and h.get('month') and h.get('user_id') == obj_user_id})
            if not months_for_year:
                months_for_year = [datetime.now().month]
            month = st.selectbox("Month", options=months_for_year, index=0, key="highlight_month", on_change=lambda: set_active_tab("Monthly Highlights"))
        # Buscar highlights do banco filtrando por user_id, ano, mês, área
        highlights = get_collection_data_by_area('monthly_highlights', area_filter=area_filter, include_id=True)
        filtered = [
            h for h in highlights
            if h.get('year') == year and h.get('month') == month and h.get('user_id') == obj_user_id
        ]
        st.write("### Highlights for selected month/year")
        if filtered:
            h = filtered[0]
            pos = st.text_area("Positives (one per line)", value="\n".join([p.get('title','') for p in h.get('positive', [])]), key=f"edit_highlight_pos")
            neg = st.text_area("Negatives (one per line)", value="\n".join([n.get('title','') for n in h.get('negative', [])]), key=f"edit_highlight_neg")
            if st.button(":material/save: Save", key=f"save_highlight"):
                filter_query = {'_id': h['_id']} if '_id' in h else {'year': year, 'month': month, 'user_id': current_user_id}
                update_document('monthly_highlights', filter_query, {
                    'year': year,
                    'month': month,
                    'user_id': current_user_id,
                    'area': area_filter,
                    'positive': [{'title': t.strip()} for t in pos.splitlines() if t.strip()],
                    'negative': [{'title': t.strip()} for t in neg.splitlines() if t.strip()]
                })
                st.success("Updated!")
                st.rerun()
            confirm_delete(":material/delete: Delete", lambda: (delete_document('monthly_highlights', {'_id': h['_id']} if '_id' in h else {'year': year, 'month': month, 'user_id': current_user_id}), st.success("Deleted!"), st.rerun()), key=f"popover_highlight")
        else:
            with st.form(key="add_highlight_form"):
                pos_new = st.text_area("Positives (one per line)", key="add_highlight_pos")
                neg_new = st.text_area("Negatives (one per line)", key="add_highlight_neg")
                submitted = st.form_submit_button(":material/add: Save Highlight")
                if submitted:
                    insert_document('monthly_highlights', {
                        'year': year,
                        'month': month,
                        'user_id': current_user_id,
                        'area': area_filter,
                        'positive': [{'title': t.strip()} for t in pos_new.splitlines() if t.strip()],
                        'negative': [{'title': t.strip()} for t in neg_new.splitlines() if t.strip()]
                    })
                    st.success("Added!")
                    st.rerun()

    with tab_map["Opportunities"]:
        set_active_tab("Opportunities")
        all_opportunities = get_collection_data_by_area('monthly_opportunities', area_filter=area_filter, include_id=True)
        years = sorted({o.get('year') for o in all_opportunities if o.get('year') and o.get('user_id') == obj_user_id})
        if not years:
            years = [datetime.now().year]
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Year", options=years, index=years.index(datetime.now().year) if datetime.now().year in years else 0, key="opp_year", on_change=lambda: set_active_tab("Opportunities"))
        with col2:
            months_for_year = sorted({o.get('month') for o in all_opportunities if o.get('year') == year and o.get('month') and o.get('user_id') == obj_user_id})
            if not months_for_year:
                months_for_year = [datetime.now().month]
            month = st.selectbox("Month", options=months_for_year, index=0, key="opp_month", on_change=lambda: set_active_tab("Opportunities"))
        opportunities = get_collection_data_by_area('monthly_opportunities', area_filter=area_filter, include_id=True)
        filtered = [
            o for o in opportunities
            if o.get('year') == year and o.get('month') == month and o.get('user_id') == obj_user_id
        ]
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
                        'improvements': [im.strip() for im in improvements[i].splitlines() if im.strip()],
                        'user_id': current_user_id
                    })
                filter_query = {'_id': o['_id']} if '_id' in o else {'year': year, 'month': month, 'user_id': current_user_id}
                update_document('monthly_opportunities', filter_query, {
                    'year': year,
                    'month': month,
                    'user_id': current_user_id,
                    'area': area_filter,
                    'opportunity_list': new_blocks
                })
                st.success("Updated!")
                st.rerun()
            confirm_delete(":material/delete: Delete", lambda: (delete_document('monthly_opportunities', {'_id': o['_id']} if '_id' in o else {'year': year, 'month': month, 'user_id': current_user_id}), st.success("Deleted!"), st.rerun()), key=f"popover_opp")
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
                            'user_id': current_user_id,
                            'area': area_filter,
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
        all_plans = get_collection_data_by_area('action_plans', area_filter=area_filter, include_id=True)
        years = sorted({p.get('created_at').year for p in all_plans if p.get('created_at') and hasattr(p.get('created_at'), 'year') and p.get('user_id') == obj_user_id})
        if not years:
            years = [datetime.now().year]
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Year", options=years, index=years.index(datetime.now().year) if datetime.now().year in years else 0, key="plan_year", on_change=lambda: set_active_tab("Action Plans"))
        with col2:
            months_for_year = sorted({p.get('created_at').month for p in all_plans if p.get('created_at') and hasattr(p.get('created_at'), 'year') and p['created_at'].year == year and hasattr(p.get('created_at'), 'month') and p.get('user_id') == obj_user_id})
            if not months_for_year:
                months_for_year = [datetime.now().month]
            month = st.selectbox("Month", options=months_for_year, index=0, key="plan_month", on_change=lambda: set_active_tab("Action Plans"))
        plans = get_collection_data_by_area('action_plans', area_filter=area_filter, include_id=True)
        filtered = [
            p for p in plans
            if hasattr(p.get('created_at', None), 'year') and p['created_at'].year == year and p['created_at'].month == month and p.get('user_id') == obj_user_id
        ]
        st.write("### Action Plan for selected month/year")
        def generate_id(prefix, existing):
            idx = 1
            while f"{prefix}{idx}" in existing:
                idx += 1
            return f"{prefix}{idx}"
        def get_plan_state():
            key = f"plan_state_{year}_{month}"
            if key not in st.session_state:
                if filtered:
                    # Garantir que subplans/actions tenham id
                    plan = filtered[0].copy()
                    for sidx, sub in enumerate(plan.get('subplans', [])):
                        if 'id' not in sub or not sub['id']:
                            sub['id'] = f"sub{sidx+1}"
                        for aidx, a in enumerate(sub.get('actions', [])):
                            if 'id' not in a or not a['id']:
                                a['id'] = f"a{aidx+1}"
                    st.session_state[key] = plan
                else:
                    st.session_state[key] = {
                        'title': '',
                        'description': '',
                        'created_at': datetime(year, month, 1),
                        'subplans': []
                    }
            return st.session_state[key]
        plan_state = get_plan_state()
        with st.container(border=True):
            st.markdown("#### :material/assignment: Plan Details")
            col1, col2 = st.columns(2)
            with col1:
                plan_state['title'] = st.text_input("Title", value=plan_state.get('title',''), key=f"plan_title")
            with col2:
                plan_state['description'] = st.text_area("Description", value=plan_state.get('description',''), key=f"plan_desc")
        st.markdown("---")
        st.markdown(":material/list: **Subplans**")
        subplan_changed = False
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
                action_changed = False
                for aidx, a in enumerate(sub.get('actions', [])):
                    with st.container(border=True):
                        ac1, ac2, ac3, ac4, ac5 = st.columns([3,1.5,1.75,1.75,1], vertical_alignment="center")
                        with ac1:
                            a['title'] = st.text_input("Action Title", value=a.get('title',''), key=f"action_title_{sidx}_{aidx}")
                        with ac2:
                            a['status'] = st.selectbox(
                                "Status",
                                options=["Pending", "Completed"],
                                index=["Pending", "Completed"].index(a.get('status', 'Pending')) if a.get('status', 'Pending') in ["Pending", "Completed"] else 0,
                                key=f"action_status_{sidx}_{aidx}"
                            )
                        with ac3:
                            a['due_date'] = st.date_input("Due Date", value=pd.to_datetime(a.get('due_date')) if a.get('due_date') else datetime(year, month, 1), key=f"action_due_{sidx}_{aidx}")
                        with ac4:
                            responsible_options = [
                                "Ananda", "Diego", "Eleana", "Felipe", "Guilherme", "Italo", "Josimar", "Leonardo", "Paula", "Thiago", "Victor Paiva", "Vinicius", "Vitor Bitencourt", "Williana"
                            ]
                            responsible_options.sort()
                            a['responsible'] = st.selectbox(
                                "Responsible",
                                options=responsible_options,
                                index=responsible_options.index(a.get('responsible')) if a.get('responsible') in responsible_options else 0,
                                key=f"action_resp_{sidx}_{aidx}",
                                placeholder="Select or type...",
                                accept_new_options=True
                            )
                        with ac5:
                            if st.button(":material/delete:", key=f"remove_action_{sidx}_{aidx}"):
                                sub['actions'].pop(aidx)
                                action_changed = True
                        if 'id' not in a or not a['id']:
                            a['id'] = f"a{aidx+1}"
                if action_changed:
                    st.rerun()
                if st.button(":material/add: Add Action", key=f"add_action_{sidx}"):
                    if 'actions' not in sub:
                        sub['actions'] = []
                    existing_ids = {a['id'] for a in sub['actions'] if 'id' in a}
                    new_id = generate_id('a', existing_ids)
                    sub['actions'].append({
                        'id': new_id, 'title': '', 'status': 'Pending', 'due_date': datetime(year, month, 1), 'responsible': ''
                    })
                    st.rerun()
                if 'id' not in sub or not sub['id']:
                    sub['id'] = f"sub{sidx+1}"
        if subplan_changed:
            st.rerun()
        if st.button(":material/add: Add Subplan", key="add_subplan"):
            existing_ids = {s['id'] for s in plan_state['subplans'] if 'id' in s}
            new_id = generate_id('sub', existing_ids)
            plan_state['subplans'].append({
                'id': new_id, 'title': '', 'reason': '', 'start_date': datetime(year, month, 1), 'end_date': datetime(year, month, 1), 'actions': []
            })
            st.rerun()
        st.markdown("---")
        # Verificação de datas inválidas nas ações
        invalid_due_date = False
        for sub in plan_state['subplans']:
            for a in sub.get('actions', []):
                due = a.get('due_date')
                if due and pd.to_datetime(due).date() < date.today():
                    invalid_due_date = True
                    break
            if invalid_due_date:
                break
        if invalid_due_date:
            st.warning(':material/error: Existem ações com data inferior à data de hoje. Corrija para salvar o plano.')
        col_save, col_delete = st.columns([2,1]); save_success = False
        with col_save:
            if st.button(":material/save: Save Action Plan", key=f"save_plan", type="primary", disabled=invalid_due_date):
                def ensure_datetime(obj):
                    if isinstance(obj, datetime):
                        return obj
                    elif hasattr(obj, 'year') and hasattr(obj, 'month') and hasattr(obj, 'day'):
                        return datetime(obj.year, obj.month, obj.day)
                    return obj
                new_subplans = []
                for sidx, sub in enumerate(plan_state['subplans']):
                    new_sub = {
                        'id': sub.get('id', f'sub{sidx+1}'),
                        'title': st.session_state.get(f"subplan_title_{sidx}", sub.get('title', '')),
                        'reason': st.session_state.get(f"subplan_reason_{sidx}", sub.get('reason', '')),
                        'start_date': ensure_datetime(st.session_state.get(f"subplan_start_{sidx}", sub.get('start_date'))),
                        'end_date': ensure_datetime(st.session_state.get(f"subplan_end_{sidx}", sub.get('end_date'))),
                        'actions': []
                    }
                    for aidx, a in enumerate(sub.get('actions', [])):
                        new_action = {
                            'id': a.get('id', f'a{aidx+1}'),
                            'title': st.session_state.get(f"action_title_{sidx}_{aidx}", a.get('title', '')),
                            'status': st.session_state.get(f"action_status_{sidx}_{aidx}", a.get('status', '')),
                            'due_date': ensure_datetime(st.session_state.get(f"action_due_{sidx}_{aidx}", a.get('due_date'))),
                            'responsible': st.session_state.get(f"action_resp_{sidx}_{aidx}", a.get('responsible', ''))
                        }
                        new_sub['actions'].append(new_action)
                    new_subplans.append(new_sub)
                plan_state['subplans'] = new_subplans
                plan_state['created_at'] = ensure_datetime(plan_state.get('created_at'))
                try:
                    plan_state['user_id'] = ObjectId(current_user_id)
                    plan_state['area'] = area_filter
                    if filtered:
                        filter_query = {'_id': filtered[0]['_id']} if '_id' in filtered[0] else {'year': year, 'month': month, 'user_id': current_user_id}
                        update_document('action_plans', filter_query, plan_state)
                        st.success("Updated!")
                    else:
                        insert_document('action_plans', plan_state)
                        st.success("Created!")
                    save_success = True
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
        with col_delete:
            def delete_plan():
                try:
                    filter_query = {'_id': filtered[0]['_id']} if filtered and '_id' in filtered[0] else {'year': year, 'month': month, 'user_id': current_user_id}
                    delete_document('action_plans', filter_query)
                    st.success("Deleted!")
                    st.session_state['modal_open'] = False
                    st.session_state['show_manage_modal'] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao deletar: {e}")
            if filtered:
                confirm_delete(":material/delete: Delete", delete_plan, key=f"popover_plan")
        if save_success:
            st.session_state['modal_open'] = False
            st.session_state['show_manage_modal'] = False
            st.rerun()

def show_manage_modal():
    """Exibe o modal de gerenciamento de dados, controlando tudo por tabs internas."""
    if st.session_state.get('show_manage_modal', False):
        print("DEBUG: show_manage_modal chamada - abrindo modal")
        _modal_dialog() 