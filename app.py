import streamlit as st
import pandas as pd
import os

from database.connection import DB_FILE, get_conn, init_db_once
from database.queries import get_current_date_name
from database.cache import cached_get_events
from components.modals import add_vendor_modal
from views.tab_dados import render_tab_dados
from views.tab_rodadas import render_tab_rodadas
from views.tab_sangria import render_tab_sangria
from views.tab_fechamento import render_tab_fechamento
from views.tab_logs import render_tab_logs

st.set_page_config(page_title="Gestão de Bingo 2026", layout="wide", page_icon="🎱")

def check_password():
    """Valida o usuário e a senha verificando no st.secrets"""
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Acesso Restrito")
    with st.form("login_form"):
        username_input = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        
        if submitted:
            try:
                usernames_dict = st.secrets["credentials"]["usernames"]
                user = str(username_input).strip()
                digitada = str(pwd).strip()
                
                if user in usernames_dict and usernames_dict[user] == digitada:
                    st.session_state["password_correct"] = True
                    st.session_state["logged_user"] = user
                    st.rerun()
                else:
                    st.error("😕 Usuário ou senha incorretos.")
            except KeyError:
                st.error("Erro: secrets.toml não configurado na chave [credentials] usernames.")
                
    return False

if not check_password():
    st.stop()

# Inicializa banco de dados (apenas 1x por sessão do servidor)
init_db_once()

# Sidebar para Gestão de Eventos
st.sidebar.title("📅 Gestão de Eventos")

# Indicador de conexão (sem abrir conexão extra)
_is_postgres = "connections" in st.secrets or "postgres" in st.secrets
if _is_postgres:
    st.sidebar.success("🟢 Conectado à Nuvem (Supabase)")
else:
    st.sidebar.warning("🟡 Modo de Segurança: Banco Local (SQLite)")

# Leitura de eventos via cache (evita query ao Supabase a cada render)
df_events = cached_get_events()

with st.sidebar.expander("➕ Novo Evento", expanded=False):
    novo_nome = st.text_input("Nome do Evento", value=get_current_date_name())
    if st.button("Criar Evento", use_container_width=True, type="primary"):
        if novo_nome:
            try:
                _conn = get_conn()
                _conn.execute("INSERT INTO events (name) VALUES (%s) ON CONFLICT (name) DO NOTHING" if _is_postgres else "INSERT OR IGNORE INTO events (name) VALUES (?)", (novo_nome,))
                _conn.commit()
                _conn.close()
                st.success(f"Evento criado!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error("Já existe um evento com este nome.")

if df_events.empty:
    st.sidebar.warning("Nenhum evento criado. Crie um evento para começar.")
    st.title("🎱 Sistema de Controle do Bingo 2026")
    st.info("⬅️ Crie um evento na barra lateral para iniciar.")
    st.stop()

# Seleção de Evento
event_options = df_events.apply(lambda x: f"[{x['id']}] {x['name']}", axis=1).tolist()
selected_event_str = st.sidebar.selectbox("Evento Ativo", event_options)
active_event_id = int(selected_event_str.split(']')[0][1:])
active_event_name = selected_event_str.split('] ')[1]

st.sidebar.success(f"Ativo: {active_event_name}")

st.sidebar.divider()
st.sidebar.subheader("👤 Vendedores")
if st.sidebar.button("➕ Novo Vendedor", use_container_width=True):
    add_vendor_modal()

st.sidebar.divider()
current_user = st.session_state.get("logged_user", "Usuário")
st.sidebar.markdown(f"**Bem-vindo, {current_user.capitalize()}!**")
if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
    st.session_state["password_correct"] = False
    st.session_state["logged_user"] = None
    st.rerun()

# Interface Principal
st.title(f"🎱 Sistema de Controle - {active_event_name}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚙️ Dados do Dia", "🎯 Rodadas e Vendedores", "💰 Sangria", "📊 Fechamento", "📋 Logs"])

with tab1:
    render_tab_dados(active_event_id)

with tab2:
    render_tab_rodadas(active_event_id)

with tab3:
    render_tab_sangria(active_event_id)

with tab4:
    render_tab_fechamento(active_event_id)

with tab5:
    render_tab_logs(active_event_id)
