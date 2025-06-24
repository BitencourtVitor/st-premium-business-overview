import streamlit as st
import pandas as pd
from datetime import datetime
from database.mongodb_utils import get_collection_data_by_area, insert_document, update_document, delete_document

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
    area_filter = 'permit' if current_page == 'permit_control' else 'accounting'
    
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

    with tab_map["Monthly Highlights"]:
        set_active_tab("Monthly Highlights")
        years = sorted({h.get('year') for h in get_collection_data_by_area('monthly_highlights', area_filter=area_filter) if h.get('year')})
        
        # Se não há anos disponíveis, usar o ano atual
        if not years:
            years = [datetime.now().year]
            
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Year", options=years, index=years.index(datetime.now().year) if datetime.now().year in years else 0, key="highlight_year", on_change=lambda: set_active_tab("Monthly Highlights"))
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=st.session_state.get("highlight_month", datetime.now().month), step=1, key="highlight_month", on_change=lambda: set_active_tab("Monthly Highlights"))
        
        # Validar que year e month não são None
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
            
        highlights = get_collection_data_by_area('monthly_highlights', area_filter=area_filter)
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
                    'user_id': current_user_id,
                    'area': area_filter,
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
                        'user_id': current_user_id,
                        'area': area_filter,
                        'positive': [{'title': t.strip()} for t in pos_new.splitlines() if t.strip()],
                        'negative': [{'title': t.strip()} for t in neg_new.splitlines() if t.strip()]
                    })
                    st.success("Added!")
                    st.rerun()

    with tab_map["Opportunities"]:
        set_active_tab("Opportunities")
        years = sorted({o.get('year') for o in get_collection_data_by_area('monthly_opportunities', area_filter=area_filter) if o.get('year')})
        
        # Se não há anos disponíveis, usar o ano atual
        if not years:
            years = [datetime.now().year]
            
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Year", options=years, index=years.index(datetime.now().year) if datetime.now().year in years else 0, key="opp_year", on_change=lambda: set_active_tab("Opportunities"))
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=st.session_state.get("opp_month", datetime.now().month), step=1, key="opp_month", on_change=lambda: set_active_tab("Opportunities"))
        
        # Validar que year e month não são None
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
            
        opportunities = get_collection_data_by_area('monthly_opportunities', area_filter=area_filter)
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
                        'improvements': [im.strip() for im in improvements[i].splitlines() if im.strip()],
                        'user_id': current_user_id
                    })
                update_document('monthly_opportunities', {'year': year, 'month': month}, {
                    'year': year,
                    'month': month,
                    'user_id': current_user_id,
                    'area': area_filter,
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
        years = sorted({p.get('created_at').year for p in get_collection_data_by_area('action_plans', area_filter=area_filter) if p.get('created_at') and hasattr(p.get('created_at'), 'year')})
        
        # Se não há anos disponíveis, usar o ano atual
        if not years:
            years = [datetime.now().year]
        
        col1, col2 = st.columns(2)
        with col1:
            year = st.selectbox("Year", options=years, index=years.index(datetime.now().year) if datetime.now().year in years else 0, key="plan_year", on_change=lambda: set_active_tab("Action Plans"))
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=st.session_state.get("plan_month", datetime.now().month), step=1, key="plan_month", on_change=lambda: set_active_tab("Action Plans"))
        
        # Validar que year e month não são None
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
            
        plans = get_collection_data_by_area('action_plans', area_filter=area_filter)
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
                        plan_state['user_id'] = current_user_id
                        plan_state['area'] = area_filter
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
                        plan_state['user_id'] = current_user_id
                        plan_state['area'] = area_filter
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
    """Exibe o modal de gerenciamento de dados, controlando tudo por tabs internas."""
    if st.session_state.get('show_manage_modal', False):
        print("DEBUG: show_manage_modal chamada - abrindo modal")
        _modal_dialog() 