import streamlit as st
import pandas as pd
from database.connection import get_conn
from database.queries import get_setting, set_setting, log_action

def render_tab_fechamento(active_event_id):
    st.header("Fechamento do Evento")
    
    colA, colB = st.columns([1, 2])
    with colA:
        st.subheader("Dinheiro em Caixa")
        current_dinheiro = get_setting(active_event_id, 'dinheiro_fechamento', 0.0)
        dinheiro_fechamento = st.number_input("Valor em Dinheiro Existente (R$)", min_value=0.0, step=10.0, value=float(current_dinheiro), format="%.2f")
        if st.button("Salvar Valor em Caixa"):
            set_setting(active_event_id, 'dinheiro_fechamento', dinheiro_fechamento)
            log_action(active_event_id, f"Definiu o dinheiro final em caixa como R$ {dinheiro_fechamento:.2f}")
            st.success("Valor em caixa salvo para este evento!")
            st.rerun()
            
    with colB:
        st.subheader("Troco Devolvido pelos Vendedores")
        conn = get_conn()
        query_v_fechamento = '''
            SELECT v.id, v.name, COALESCE(ev.troco_enviado, 0.0) as troco_enviado, COALESCE(ev.troco_devolvido, 0.0) as troco_devolvido
            FROM vendors v
            LEFT JOIN event_vendors ev ON v.id = ev.vendor_id AND ev.event_id = ?
        '''
        df_v_fechamento = pd.read_sql(query_v_fechamento, conn, params=(active_event_id,))
        
        df_v_fechamento_ativo = df_v_fechamento[df_v_fechamento['troco_enviado'] > 0].copy()
        
        if not df_v_fechamento_ativo.empty:
            edited_v_fechamento = st.data_editor(
                df_v_fechamento_ativo,
                column_config={
                    "id": None,
                    "name": st.column_config.TextColumn("Vendedor", disabled=True),
                    "troco_enviado": st.column_config.NumberColumn("Troco Enviado (R$)", disabled=True, format="R$ %.2f"),
                    "troco_devolvido": st.column_config.NumberColumn("Troco Devolvido (R$)", min_value=0.0, format="R$ %.2f")
                },
                hide_index=True,
                use_container_width=True
            )
            if st.button("Atualizar Troco Devolvido"):
                for _, row in edited_v_fechamento.iterrows():
                    td = row['troco_devolvido'] if pd.notna(row['troco_devolvido']) else 0.0
                    vid = int(row['id'])
                    conn.execute("UPDATE event_vendors SET troco_devolvido=? WHERE event_id=? AND vendor_id=?", (td, active_event_id, vid))
                conn.commit()
                log_action(active_event_id, "Atualizou os valores de troco devolvido pelos vendedores no fechamento.")
                st.success("Troco devolvido atualizado!")
                st.rerun()
        else:
            st.info("Nenhum vendedor recebeu troco neste evento.")

    st.divider()
    
    df_rounds_f = pd.read_sql('SELECT * FROM rounds WHERE event_id=?', conn, params=(active_event_id,))
    
    if not df_rounds_f.empty:
        r_ids = df_rounds_f['id'].tolist()
        placeholders = ','.join('?' for _ in r_ids)
        df_vr_f = pd.read_sql(f'SELECT * FROM vendor_rounds WHERE round_id IN ({placeholders})', conn, params=r_ids)
    else:
        df_vr_f = pd.DataFrame()
        
    df_s_f = pd.read_sql('SELECT * FROM sangrias WHERE event_id=?', conn, params=(active_event_id,))
    
    caixa_inicial = get_setting(active_event_id, 'caixa_inicial', 0.0)
    dinheiro_caixa_final = get_setting(active_event_id, 'dinheiro_fechamento', 0.0)
    
    receita_total_teorica = 0.0
    total_cartelas_evento = 0
    
    if not df_rounds_f.empty and not df_vr_f.empty:
        for _, r in df_rounds_f.iterrows():
            r_id = r['id']
            r_price = float(r['valor_cartela'])
            df_vr_round = df_vr_f[df_vr_f['round_id'] == r_id]
            
            if not df_vr_round.empty:
                v = df_vr_round['cartelas_recebidas'] + df_vr_round['cartelas_adicionais'] - df_vr_round['cartelas_devolvidas']
                v_sum = v.sum()
                total_cartelas_evento += v_sum
                receita_total_teorica += v_sum * r_price

    total_sangrias = df_s_f['valor'].sum() if not df_s_f.empty else 0.0
    SD = total_sangrias + dinheiro_caixa_final
    
    TP = df_vr_f['val_pix'].sum() if not df_vr_f.empty else 0.0
    TS = df_vr_f['val_santa_ficha'].sum() if not df_vr_f.empty else 0.0
    TD = df_vr_f['val_debito'].sum() if not df_vr_f.empty else 0.0
    
    quebra = receita_total_teorica + caixa_inicial - SD - TP - TS - TD
    
    VC = SD + TP + TS + TD
    RL = VC - caixa_inicial
    
    conn.close()
    
    st.subheader("Resumo dos Indicadores Finais do Evento")
    
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("Receita Total Bruta (Teórica)", f"R$ {receita_total_teorica:.2f}")
    rc2.metric("Receita Líquida", f"R$ {RL:.2f}")
    
    if quebra != 0:
        if quebra > 0:
            rc3.metric("Quebra de Caixa", f"R$ {quebra:.2f} (Falta)", delta=f"-R$ {quebra:.2f}", delta_color="inverse")
        else:
            rc3.metric("Quebra de Caixa", f"R$ {abs(quebra):.2f} (Sobra)", delta=f"+R$ {abs(quebra):.2f}", delta_color="normal")
    else:
        rc3.metric("Quebra de Caixa", "R$ 0.00 (Perfeito)")
        
    rc4.metric("Total de Cartelas Vendidas", int(total_cartelas_evento))
    
    st.write("### Detalhamento por Forma de Pagamento")
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("Total de Sangrias", f"R$ {total_sangrias:.2f}")
    mc2.metric("Dinheiro Final em Caixa", f"R$ {dinheiro_caixa_final:.2f}")
    mc3.metric("Total Pix", f"R$ {TP:.2f}")
    mc4.metric("Total Santa Ficha", f"R$ {TS:.2f}")
    mc5.metric("Total Débito", f"R$ {TD:.2f}")

    with st.expander("Ver Fórmulas de Fechamento"):
        st.markdown(f'''
        **Caixa Inicial (CI):** R$ {caixa_inicial:.2f}
        **Receita Total (RT):** R$ {receita_total_teorica:.2f}
        **Total de Sangria + Caixa Final (SD):** R$ {SD:.2f} (R$ {total_sangrias:.2f} + R$ {dinheiro_caixa_final:.2f})
        **Total PIX (TP):** R$ {TP:.2f}
        **Total Santa Ficha (TS):** R$ {TS:.2f}
        **Total Débito (TD):** R$ {TD:.2f}
        
        **Quebra = RT + CI - SD - TP - TS - TD**
        Quebra = {receita_total_teorica:.2f} + {caixa_inicial:.2f} - {SD:.2f} - {TP:.2f} - {TS:.2f} - {TD:.2f} = **R$ {quebra:.2f}**
        
        **Valor Consolidado (VC) = SD + TP + TS + TD**
        VC = {SD:.2f} + {TP:.2f} + {TS:.2f} + {TD:.2f} = **R$ {VC:.2f}**
        
        **Receita Líquida (RL) = VC - CI**
        RL = {VC:.2f} - {caixa_inicial:.2f} = **R$ {RL:.2f}**
        ''')
