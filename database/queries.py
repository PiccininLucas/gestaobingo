import streamlit as st
import datetime
from database.connection import get_conn

def get_setting(event_id, key, default=0.0):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE event_id = ? AND key = ?', (event_id, key))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(event_id, key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO settings (event_id, key, value) 
        VALUES (?, ?, ?) 
        ON CONFLICT(event_id, key) DO UPDATE SET value=excluded.value
    ''', (event_id, key, value))
    conn.commit()
    conn.close()
    # Invalida cache para que leituras seguintes reflitam o novo valor
    st.cache_data.clear()

def log_action(event_id, action):
    conn = get_conn()
    username = st.session_state.get("logged_user", "Sistema")
    try:
        conn.execute("INSERT INTO audit_logs (event_id, action, username) VALUES (?, ?, ?)", (event_id, action, username))
    except Exception as e:
        if hasattr(conn, 'is_postgres'):
            conn.conn.rollback()
        conn.execute("INSERT INTO audit_logs (event_id, action) VALUES (?, ?)", (event_id, action))
    conn.commit()
    conn.close()
    # Invalida cache para que o log apareça imediatamente
    st.cache_data.clear()

def get_current_date_name():
    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    hoje = datetime.datetime.now()
    dia_nome = dias_semana[hoje.weekday()]
    data_str = hoje.strftime("%d/%m")
    return f"{dia_nome} {data_str}"
