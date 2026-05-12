import streamlit as st
import pandas as pd
from database.cache import cached_get_logs

def render_tab_logs(active_event_id):
    st.header("Logs de Auditoria do Evento")
    st.write("Acompanhe o histórico de ações e edições importantes realizadas neste evento.")
    
    # Leitura via cache — sem query direta ao Supabase
    df_logs = cached_get_logs(active_event_id).copy()
    
    if not df_logs.empty:
        df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp']).dt.strftime('%d/%m/%Y %H:%M:%S')
        
        col_config = {
            "timestamp": "Data / Hora",
            "action": st.column_config.TextColumn("Descrição da Ação")
        }
        if 'username' in df_logs.columns:
            col_config["username"] = "Usuário"
            
        st.dataframe(
            df_logs,
            column_config=col_config,
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nenhuma atividade registrada para este evento ainda.")
