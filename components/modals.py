import streamlit as st
import sqlite3
from database.connection import get_conn
from database.queries import log_action

@st.dialog("Cadastrar Novo Vendedor")
def add_vendor_modal():
    vname = st.text_input("Nome do Vendedor")
    if st.button("Salvar Vendedor", type="primary"):
        if vname:
            conn = get_conn()
            try:
                conn.execute("INSERT INTO vendors (name) VALUES (?)", (vname,))
                conn.commit()
                st.success(f"Vendedor {vname} cadastrado com sucesso!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                err_str = str(e)
                if "UNIQUE constraint failed" in err_str or "UniqueViolation" in err_type_check(e):
                    st.error("Este vendedor já existe.")
                else:
                    st.error(f"Erro: {err_str}")
            finally:
                conn.close()
        else:
            st.error("Informe o nome do vendedor.")

def err_type_check(e):
    return type(e).__name__

@st.dialog("Criar Nova Rodada")
def add_round_modal(event_id):
    round_type = st.selectbox("Tipo de Rodada", ["Geral", "Extra", "Dinheiro"])
    name = st.text_input("Sequência / Nome (ex: A, B, 1, 2)")
    valor_cartela = st.number_input("Valor da Cartela (R$)", min_value=0.0, step=0.5, format="%.2f")
    
    if st.button("Salvar Rodada", type="primary"):
        if name:
            conn = get_conn()
            try:
                conn.execute("INSERT INTO rounds (event_id, round_type, name, valor_cartela) VALUES (?, ?, ?, ?)", (event_id, round_type, name, valor_cartela))
                conn.commit()
                log_action(event_id, f"Criou a rodada {round_type} - {name} com cartela a R$ {valor_cartela:.2f}")
                st.success(f"Rodada {round_type} - {name} criada com sucesso!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                err_str = str(e)
                if "UNIQUE constraint failed" in err_str or "UniqueViolation" in err_type_check(e):
                    st.error("Esta rodada já existe neste evento.")
                else:
                    st.error(f"Erro: {err_str}")
            finally:
                conn.close()
        else:
            st.error("Informe a sequência/nome da rodada.")

@st.dialog("Registro de Vendedor")
def open_vendor_modal(r_id, vid, vname, r_price, event_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM vendor_rounds WHERE round_id=? AND vendor_id=?', (r_id, vid))
    vr_row = c.fetchone()
    conn.close()
    
    vr_cr = vr_row[3] if vr_row else 0
    vr_ca = vr_row[4] if vr_row else 0
    vr_cd = vr_row[5] if vr_row else 0
    vr_vd = vr_row[6] if vr_row else 0.0
    vr_vp = vr_row[7] if vr_row else 0.0
    vr_vsf = vr_row[8] if vr_row else 0.0
    vr_vdeb = vr_row[9] if vr_row else 0.0

    st.markdown(f"### 👤 {vname}")
    
    with st.expander("Controle de Cartelas", expanded=True):
        cr = st.number_input("Recebidas", min_value=0, value=int(vr_cr), step=1, key=f"m_cr_{r_id}_{vid}")
        ca = st.number_input("Adicionais", min_value=0, value=int(vr_ca), step=1, key=f"m_ca_{r_id}_{vid}")
        cd = st.number_input("Devolvidas", min_value=0, value=int(vr_cd), step=1, key=f"m_cd_{r_id}_{vid}")
    
    cartelas_vendidas = cr + ca - cd
    valor_esperado = cartelas_vendidas * r_price
    
    with st.expander("Valores Devolvidos (R$)", expanded=True):
        vd = st.number_input("Dinheiro", min_value=0.0, value=float(vr_vd), step=5.0, format="%.2f", key=f"m_vd_{r_id}_{vid}")
        vp = st.number_input("Pix", min_value=0.0, value=float(vr_vp), step=5.0, format="%.2f", key=f"m_vp_{r_id}_{vid}")
        vsf = st.number_input("Santa Ficha", min_value=0.0, value=float(vr_vsf), step=5.0, format="%.2f", key=f"m_vsf_{r_id}_{vid}")
        vdeb = st.number_input("Débito", min_value=0.0, value=float(vr_vdeb), step=5.0, format="%.2f", key=f"m_vdeb_{r_id}_{vid}")
        
    valor_devolvido = vd + vp + vsf + vdeb
    diferenca = valor_esperado - valor_devolvido
    
    st.markdown(f"**Cartelas Vendidas:** {cartelas_vendidas}")
    st.markdown(f"**Valor Esperado:** R$ {valor_esperado:.2f}")
    st.markdown(f"**Valor Devolvido:** R$ {valor_devolvido:.2f}")
    
    if abs(diferenca) > 0.01:
        if diferenca > 0:
            st.error(f"Faltando: R$ {diferenca:.2f}")
        else:
            st.warning(f"Excedente: R$ {abs(diferenca):.2f}")
    else:
        st.success("Tudo certo! (Diferença: R$ 0.00)")
        
    if st.button("💾 Salvar Registro", key=f"m_btn_{r_id}_{vid}", use_container_width=True):
        conn_local = get_conn()
        conn_local.execute('''
            INSERT INTO vendor_rounds (round_id, vendor_id, cartelas_recebidas, cartelas_adicionais, cartelas_devolvidas, val_dinheiro, val_pix, val_santa_ficha, val_debito)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(round_id, vendor_id) DO UPDATE SET
                cartelas_recebidas=excluded.cartelas_recebidas,
                cartelas_adicionais=excluded.cartelas_adicionais,
                cartelas_devolvidas=excluded.cartelas_devolvidas,
                val_dinheiro=excluded.val_dinheiro,
                val_pix=excluded.val_pix,
                val_santa_ficha=excluded.val_santa_ficha,
                val_debito=excluded.val_debito
        ''', (r_id, vid, cr, ca, cd, vd, vp, vsf, vdeb))
        conn_local.commit()
        conn_local.close()
        log_action(event_id, f"Salvou registro do vendedor {vname} na rodada ID {r_id} (Cartelas vendidas: {cartelas_vendidas}, Devolvido: R$ {valor_devolvido:.2f})")
        st.toast(f"Registro de {vname} salvo!")
        st.cache_data.clear()
        st.rerun()
