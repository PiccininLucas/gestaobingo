import streamlit as st
import pandas as pd
from database.connection import get_conn
from database.queries import get_setting, set_setting, log_action

def render_tab_dados(active_event_id):
    st.header("Dados Iniciais do Evento")
    
    colA, colB = st.columns([1, 2])
    with colA:
        current_caixa = get_setting(active_event_id, 'caixa_inicial', 0.0)
        caixa_inicial = st.number_input("Valor do Caixa Inicial (R$)", min_value=0.0, step=10.0, value=float(current_caixa), format="%.2f")
        if st.button("Salvar Caixa Inicial", type="primary"):
            set_setting(active_event_id, 'caixa_inicial', caixa_inicial)
            log_action(active_event_id, f"Definiu o caixa inicial como R$ {caixa_inicial:.2f}")
            st.success("Caixa inicial salvo para este evento!")
            
    with colB:
        st.subheader("Gestão de Vendedores no Evento")
        st.write("Marque os vendedores ativos neste evento e lance o Troco Enviado.")
        conn = get_conn()
        
        query = '''
            SELECT v.id, v.name, COALESCE(ev.is_active, FALSE) as is_active, COALESCE(ev.troco_enviado, 0.0) as troco_enviado
            FROM vendors v
            LEFT JOIN event_vendors ev ON v.id = ev.vendor_id AND ev.event_id = ?
        '''
        df_vendors = pd.read_sql(query, conn, params=(active_event_id,))
        df_vendors['is_active'] = df_vendors['is_active'].astype(bool)
        
        edited_vendors = st.data_editor(
            df_vendors,
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
            existing_ids = edited_vendors['id'].dropna().astype(int).tolist()
            if existing_ids:
                placeholders = ','.join('?' for _ in existing_ids)
                conn.execute(f"DELETE FROM vendors WHERE id NOT IN ({placeholders})", existing_ids)
            else:
                conn.execute("DELETE FROM vendors")

            for _, row in edited_vendors.iterrows():
                name = row['name'] if pd.notna(row['name']) else ""
                is_active = bool(row['is_active']) if pd.notna(row['is_active']) else True
                t_env = row['troco_enviado'] if pd.notna(row['troco_enviado']) else 0.0
                
                if pd.isna(row['id']) and name:
                    c = conn.execute("INSERT INTO vendors (name) VALUES (%s) ON CONFLICT (name) DO NOTHING" if hasattr(conn, 'is_postgres') else "INSERT OR IGNORE INTO vendors (name) VALUES (?)", (name,))
                    vid = c.lastrowid
                    if vid is None:
                        c_find = conn.execute("SELECT id FROM vendors WHERE name=?", (name,))
                        vid = c_find.fetchone()[0]
                    
                    conn.execute("""
                        INSERT INTO event_vendors (event_id, vendor_id, is_active, troco_enviado) 
                        VALUES (?, ?, ?, ?) 
                        ON CONFLICT(event_id, vendor_id) DO UPDATE SET is_active=excluded.is_active, troco_enviado=excluded.troco_enviado
                    """, (active_event_id, vid, is_active, t_env))
                    
                elif not pd.isna(row['id']):
                    vid = int(row['id'])
                    conn.execute("UPDATE vendors SET name=? WHERE id=?", (name, vid))
                    conn.execute("""
                        INSERT INTO event_vendors (event_id, vendor_id, is_active, troco_enviado) 
                        VALUES (?, ?, ?, ?) 
                        ON CONFLICT(event_id, vendor_id) DO UPDATE SET is_active=excluded.is_active, troco_enviado=excluded.troco_enviado
                    """, (active_event_id, vid, is_active, t_env))
                    
            conn.commit()
            conn.close()
            log_action(active_event_id, "Atualizou a lista de vendedores ativos e os trocos enviados.")
            st.success("Vendedores e trocos atualizados com sucesso!")
            st.rerun()
        else:
            conn.close()
