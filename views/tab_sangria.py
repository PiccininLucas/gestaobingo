import streamlit as st
import pandas as pd
from database.connection import get_conn
from database.queries import log_action
from database.cache import cached_get_sangrias

def render_tab_sangria(active_event_id):
    st.header("Sangria (Envio de Dinheiro ao Caixa Central)")
    st.write("Registre os valores em dinheiro que foram retirados do caixa para envio ao caixa central neste evento.")
    
    sangria_val = st.number_input("Valor da Sangria (R$)", min_value=0.0, step=10.0, format="%.2f")
    if st.button("Registrar Sangria", type="primary"):
        if sangria_val > 0:
            conn = get_conn()
            conn.execute(
                "INSERT INTO sangrias (event_id, valor) VALUES (%s, %s)"
                if hasattr(conn, 'is_postgres')
                else "INSERT INTO sangrias (event_id, valor) VALUES (?, ?)",
                (active_event_id, sangria_val)
            )
            conn.commit()
            conn.close()
            log_action(active_event_id, f"Registrou uma sangria de R$ {sangria_val:.2f}")
            st.cache_data.clear()
            st.success(f"Sangria de R$ {sangria_val:.2f} registrada com sucesso!")
        else:
            st.error("O valor deve ser maior que zero.")
            
    st.subheader("Histórico de Sangrias")

    # Leitura via cache — sem query direta
    df_sangrias = cached_get_sangrias(active_event_id).copy()
    
    if not df_sangrias.empty:
        df_sangrias['timestamp'] = pd.to_datetime(df_sangrias['timestamp']).dt.strftime('%d/%m/%Y %H:%M:%S')
        st.dataframe(
            df_sangrias,
            column_config={
                "id": None,
                "timestamp": "Data/Hora",
                "valor": st.column_config.NumberColumn("Valor Enviado", format="R$ %.2f")
            },
            hide_index=True,
            use_container_width=True
        )
        total_sangria = df_sangrias['valor'].sum()
        st.metric("Total de Sangrias Realizadas", f"R$ {total_sangria:.2f}")
    else:
        st.info("Nenhuma sangria registrada neste evento.")
