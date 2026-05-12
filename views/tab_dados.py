import streamlit as st
import pandas as pd
from database.connection import get_conn
from database.queries import set_setting, log_action
from database.cache import cached_get_vendors, cached_get_setting

def render_tab_dados(active_event_id):
    st.header("Dados Iniciais do Evento")
    
    colA, colB = st.columns([1, 2])
    with colA:
        # Leitura via cache — sem query ao Supabase aqui
        current_caixa = cached_get_setting(active_event_id, 'caixa_inicial', 0.0)
        caixa_inicial = st.number_input("Valor do Caixa Inicial (R$)", min_value=0.0, step=10.0, value=float(current_caixa), format="%.2f")
        if st.button("Salvar Caixa Inicial", type="primary"):
            set_setting(active_event_id, 'caixa_inicial', caixa_inicial)
            log_action(active_event_id, f"Definiu o caixa inicial como R$ {caixa_inicial:.2f}")
            st.cache_data.clear()
            st.success("Caixa inicial salvo para este evento!")
            
    with colB:
        st.subheader("Gestão de Vendedores no Evento")
        st.write("Marque os vendedores ativos neste evento e lance o Troco Enviado.")

        # Leitura via cache — evita query a cada render
        df_vendors = cached_get_vendors(active_event_id).copy()
        df_vendors['is_active'] = df_vendors['is_active'].astype(bool)
        
        # Exibe apenas colunas relevantes para esta aba
        df_edit = df_vendors[['id', 'name', 'is_active', 'troco_enviado']].copy()

        edited_vendors = st.data_editor(
            df_edit,
            column_config={
                "id": None,
                "is_active": st.column_config.CheckboxColumn("Ativo no Evento?", default=False),
                "name": st.column_config.TextColumn("Nome do Vendedor", required=True),
                "troco_enviado": st.column_config.NumberColumn("Troco Enviado (R$)", min_value=0.0, format="R$ %.2f")
            },
            hide_index=True,
            key="vendors_init_editor",
            use_container_width=True
        )
        
        if st.button("Salvar Vendedores"):
            conn = get_conn()
            existing_ids = edited_vendors['id'].dropna().astype(int).tolist()
            if existing_ids:
                placeholders = ','.join('%s' if hasattr(conn, 'is_postgres') else '?' for _ in existing_ids)
                conn.execute(f"DELETE FROM vendors WHERE id NOT IN ({placeholders})", existing_ids)
            else:
                conn.execute("DELETE FROM vendors")

            for _, row in edited_vendors.iterrows():
                name = row['name'] if pd.notna(row['name']) else ""
                is_active = bool(row['is_active']) if pd.notna(row['is_active']) else True
                t_env = row['troco_enviado'] if pd.notna(row['troco_enviado']) else 0.0
                
                if pd.isna(row['id']) and name:
                    c = conn.execute(
                        "INSERT INTO vendors (name) VALUES (%s) ON CONFLICT (name) DO NOTHING"
                        if hasattr(conn, 'is_postgres')
                        else "INSERT OR IGNORE INTO vendors (name) VALUES (?)",
                        (name,)
                    )
                    vid = c.lastrowid
                    if vid is None:
                        c_find = conn.execute(
                            "SELECT id FROM vendors WHERE name = %s"
                            if hasattr(conn, 'is_postgres')
                            else "SELECT id FROM vendors WHERE name = ?",
                            (name,)
                        )
                        vid = c_find.fetchone()[0]
                    
                    conn.execute("""
                        INSERT INTO event_vendors (event_id, vendor_id, is_active, troco_enviado) 
                        VALUES (%s, %s, %s, %s) 
                        ON CONFLICT(event_id, vendor_id) DO UPDATE SET is_active=excluded.is_active, troco_enviado=excluded.troco_enviado
                    """ if hasattr(conn, 'is_postgres') else """
                        INSERT INTO event_vendors (event_id, vendor_id, is_active, troco_enviado) 
                        VALUES (?, ?, ?, ?) 
                        ON CONFLICT(event_id, vendor_id) DO UPDATE SET is_active=excluded.is_active, troco_enviado=excluded.troco_enviado
                    """, (active_event_id, vid, is_active, t_env))
                    
                elif not pd.isna(row['id']):
                    vid = int(row['id'])
                    conn.execute(
                        "UPDATE vendors SET name = %s WHERE id = %s"
                        if hasattr(conn, 'is_postgres')
                        else "UPDATE vendors SET name = ? WHERE id = ?",
                        (name, vid)
                    )
                    conn.execute("""
                        INSERT INTO event_vendors (event_id, vendor_id, is_active, troco_enviado) 
                        VALUES (%s, %s, %s, %s) 
                        ON CONFLICT(event_id, vendor_id) DO UPDATE SET is_active=excluded.is_active, troco_enviado=excluded.troco_enviado
                    """ if hasattr(conn, 'is_postgres') else """
                        INSERT INTO event_vendors (event_id, vendor_id, is_active, troco_enviado) 
                        VALUES (?, ?, ?, ?) 
                        ON CONFLICT(event_id, vendor_id) DO UPDATE SET is_active=excluded.is_active, troco_enviado=excluded.troco_enviado
                    """, (active_event_id, vid, is_active, t_env))
                    
            conn.commit()
            conn.close()
            log_action(active_event_id, "Atualizou a lista de vendedores ativos e os trocos enviados.")
            st.cache_data.clear()
            st.success("Vendedores e trocos atualizados com sucesso!")
            st.rerun()
