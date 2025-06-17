import streamlit as st
import pandas as pd

def st_custom_metric_money(title, data, color):
    # Garante 2 casas decimais
    value = f"{data:,.2f}"
    return st.markdown(f'''
    <div class="stElementContainer element-container st-emotion-cache-11vxpcu eiemyj1" data-testid="stElementContainer" data-stale="false" width="195">
        <div class="stMetric st-emotion-cache-0 egzej5g0" data-testid="stMetric">
            <label data-testid="stMetricLabel" visibility="0" class="st-emotion-cache-17c4ue egzej5g2">
                <div class="st-emotion-cache-1wivap2 egzej5g1">
                    <div data-testid="stMarkdownContainer" class="st-emotion-cache-89jlt8 e121c1cl0">
                        <p>{title}</p>
                    </div>
                </div>
                <label class="st-emotion-cache-1whk732 e1jram343">
                    <div class="stTooltipIcon st-emotion-cache-oj1fi eqrpmav0" data-testid="stTooltipIcon">
                        <div data-testid="stTooltipHoverTarget" class="stTooltipHoverTarget" id="bui6__anchor" style="display: flex; flex-direction: row; justify-content: flex-end;"></div>
                    </div>
                </label>
            </label>
            <div data-testid="stMetricValue" class="st-emotion-cache-p38tq egzej5g3">
                <div class="st-emotion-cache-1wivap2 egzej5g1 custom-metric-money" style="color: {color}; font-size: 1.1rem; font-weight: 600;"> ${value} </div>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

def custom_divider(height="1px", margin="4px 0"):
    return st.markdown(f'''
        <div style="height:{height}; background-color:#e0e0e0; border:none; margin:{margin}; padding:0;"></div>
    ''', unsafe_allow_html=True)

def st_custom_table(df: pd.DataFrame, use_container_width: bool = True, hide_index: bool = True, **kwargs):
    """
    Exibe uma tabela personalizada usando st.dataframe com configurações padrão.
    
    Args:
        df (pd.DataFrame): DataFrame a ser exibido
        use_container_width (bool): Se True, a tabela ocupará toda a largura do container
        hide_index (bool): Se True, o índice não será exibido
        **kwargs: Argumentos adicionais para st.dataframe
    """
    return st.dataframe(
        df,
        use_container_width=use_container_width,
        hide_index=hide_index,
        **kwargs
    )