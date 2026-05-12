"""
database/cache.py
-----------------
Camada de cache para leituras do banco de dados.
Usa @st.cache_data para evitar queries repetidas ao Supabase a cada re-render.

REGRA IMPORTANTE:
  Sempre que salvar dados (INSERT/UPDATE/DELETE), chame:
      st.cache_data.clear()
  antes do st.rerun() para garantir que os dados novos apareçam.
"""

import streamlit as st
import pandas as pd
from database.connection import get_conn


@st.cache_data(ttl=30)
def cached_get_events():
    """Retorna todos os eventos ordenados pelo mais recente. Cache: 30s."""
    conn = get_conn()
    df = pd.read_sql('SELECT * FROM events ORDER BY id DESC', conn)
    conn.close()
    return df


@st.cache_data(ttl=30)
def cached_get_vendors(event_id: int):
    """Retorna todos os vendedores com status e trocos do evento. Cache: 30s."""
    conn = get_conn()
    query = '''
        SELECT v.id, v.name,
               COALESCE(ev.is_active, FALSE) as is_active,
               COALESCE(ev.troco_enviado, 0.0) as troco_enviado,
               COALESCE(ev.troco_devolvido, 0.0) as troco_devolvido
        FROM vendors v
        LEFT JOIN event_vendors ev ON v.id = ev.vendor_id AND ev.event_id = %s
    '''
    df = pd.read_sql(query, conn, params=(event_id,))
    conn.close()
    return df


@st.cache_data(ttl=30)
def cached_get_active_vendors(event_id: int):
    """Retorna apenas os vendedores ativos no evento. Cache: 30s."""
    conn = get_conn()
    query = '''
        SELECT v.id, v.name
        FROM vendors v
        JOIN event_vendors ev ON v.id = ev.vendor_id
        WHERE ev.event_id = %s AND ev.is_active = TRUE
        ORDER BY v.name
    '''
    df = pd.read_sql(query, conn, params=(event_id,))
    conn.close()
    return df


@st.cache_data(ttl=30)
def cached_get_rounds(event_id: int):
    """Retorna todas as rodadas do evento. Cache: 30s."""
    conn = get_conn()
    df = pd.read_sql(
        'SELECT * FROM rounds WHERE event_id = %s ORDER BY id',
        conn, params=(event_id,)
    )
    conn.close()
    return df


@st.cache_data(ttl=30)
def cached_get_vendor_rounds(round_id: int):
    """Retorna os registros de vendor_rounds de uma rodada. Cache: 30s."""
    conn = get_conn()
    df = pd.read_sql(
        'SELECT * FROM vendor_rounds WHERE round_id = %s',
        conn, params=(round_id,)
    )
    conn.close()
    return df


@st.cache_data(ttl=30)
def cached_get_all_vendor_rounds_for_event(event_id: int):
    """
    Retorna todos os vendor_rounds de todas as rodadas de um evento.
    Usado no fechamento para evitar N queries. Cache: 30s.
    """
    conn = get_conn()
    df = pd.read_sql(
        '''
        SELECT vr.*
        FROM vendor_rounds vr
        JOIN rounds r ON vr.round_id = r.id
        WHERE r.event_id = %s
        ''',
        conn, params=(event_id,)
    )
    conn.close()
    return df


@st.cache_data(ttl=30)
def cached_get_sangrias(event_id: int):
    """Retorna o histórico de sangrias do evento. Cache: 30s."""
    conn = get_conn()
    df = pd.read_sql(
        'SELECT id, timestamp, valor FROM sangrias WHERE event_id = %s ORDER BY timestamp DESC',
        conn, params=(event_id,)
    )
    conn.close()
    return df


@st.cache_data(ttl=30)
def cached_get_logs(event_id: int):
    """Retorna os logs de auditoria do evento. Cache: 30s."""
    conn = get_conn()
    try:
        df = pd.read_sql(
            'SELECT timestamp, username, action FROM audit_logs WHERE event_id = %s ORDER BY timestamp DESC',
            conn, params=(event_id,)
        )
    except Exception:
        df = pd.read_sql(
            'SELECT timestamp, action FROM audit_logs WHERE event_id = %s ORDER BY timestamp DESC',
            conn, params=(event_id,)
        )
    conn.close()
    return df


@st.cache_data(ttl=60)
def cached_get_setting(event_id: int, key: str, default: float = 0.0) -> float:
    """
    Retorna uma configuração do evento pelo nome da chave. Cache: 60s.
    TTL maior pois settings mudam com menos frequência.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE event_id = %s AND key = %s', (event_id, key))
    row = c.fetchone()
    conn.close()
    return float(row[0]) if row else default
