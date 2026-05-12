import streamlit as st
import pandas as pd
from database.connection import get_conn
from database.cache import cached_get_rounds, cached_get_active_vendors, cached_get_vendor_rounds
from components.modals import add_round_modal, open_vendor_modal

def render_tab_rodadas(active_event_id):
    st.header("Gestão de Rodadas")
    
    if st.button("➕ Criar Nova Rodada", type="primary"):
        add_round_modal(active_event_id)
        
    st.divider()
    
    # Leituras via cache — sem queries diretas ao Supabase
    df_rounds = cached_get_rounds(active_event_id)
    df_vendors = cached_get_active_vendors(active_event_id)
    
    if not df_rounds.empty and not df_vendors.empty:
        round_options = df_rounds.apply(
            lambda x: f"[{int(x['id'])}] {x['round_type']} - {x['name']} (R$ {x['valor_cartela']:.2f})",
            axis=1
        ).tolist()
        selected_round_str = st.selectbox("Selecione a Rodada Atual para Lançamentos", round_options)
        
        selected_round_id = int(selected_round_str.split(']')[0][1:])
        selected_round_row = df_rounds[df_rounds['id'] == selected_round_id].iloc[0]
        r_id = int(selected_round_row['id'])
        r_price = float(selected_round_row['valor_cartela'])
        
        st.subheader("Registro das Informações por Vendedor")
        st.write("Clique no **Nome do Vendedor** para abrir seu registro de cartelas e valores:")
        
        # Cache por rodada — só busca novamente após TTL ou cache.clear()
        df_vr_all = cached_get_vendor_rounds(r_id)
        registered_vids = df_vr_all['vendor_id'].tolist() if not df_vr_all.empty else []
        
        col_h1, col_h2 = st.columns([3, 1])
        col_h1.markdown("**Nome do Vendedor**")
        col_h2.markdown("**Status na Rodada**")
        st.divider()
        
        for idx, vendor in df_vendors.iterrows():
            vid = int(vendor['id'])
            vname = vendor['name']
            status = "✅ Registrado" if vid in registered_vids else "⏳ Pendente"
            
            c1, c2 = st.columns([3, 1])
            with c1:
                if st.button(vname, key=f"btn_modal_{r_id}_{vid}", use_container_width=True, type="secondary"):
                    open_vendor_modal(r_id, vid, vname, r_price, active_event_id)
            with c2:
                st.markdown(f"<div style='margin-top: 5px;'>{status}</div>", unsafe_allow_html=True)

        st.divider()
        st.header("Resultado da Rodada")
        
        df_vr = df_vr_all  # já carregado do cache acima
        if not df_vr.empty:
            df_vr = df_vr.copy()
            df_vr['vendidas'] = df_vr['cartelas_recebidas'] + df_vr['cartelas_adicionais'] - df_vr['cartelas_devolvidas']
            total_vendidas = df_vr['vendidas'].sum()
            receita_total = total_vendidas * r_price
            t_dinheiro = df_vr['val_dinheiro'].sum()
            t_pix = df_vr['val_pix'].sum()
            t_sf = df_vr['val_santa_ficha'].sum()
            t_deb = df_vr['val_debito'].sum()
            t_devolvido = t_dinheiro + t_pix + t_sf + t_deb
            t_diff = receita_total - t_devolvido
            
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Cartelas Vendidas", int(total_vendidas))
            m2.metric("Receita (Esperada)", f"R$ {receita_total:.2f}")
            m3.metric("Total Dinheiro", f"R$ {t_dinheiro:.2f}")
            m4.metric("Total Pix", f"R$ {t_pix:.2f}")
            m5.metric("Total Santa Ficha", f"R$ {t_sf:.2f}")
            m6.metric("Total Débito", f"R$ {t_deb:.2f}")
            
            if abs(t_diff) > 0.01:
                st.error(f"Divergência Total na Rodada: R$ {t_diff:.2f} (Falta)" if t_diff > 0 else f"Divergência Total na Rodada: R$ {abs(t_diff):.2f} (Excesso)")
            else:
                st.success("Caixa da rodada bateu perfeitamente!")
        else:
            st.info("Nenhum registro salvo para esta rodada ainda.")

    elif df_vendors.empty:
        st.warning("Cadastre vendedores na aba 'Dados do Dia'.")
    elif df_rounds.empty:
        st.info("Crie uma rodada para começar.")
