import streamlit as st
import pandas as pd
import sqlite3
import os

_original_read_sql = pd.read_sql
if not hasattr(pd, '_custom_read_sql_installed'):
    pd._original_read_sql_saved = pd.read_sql
    def custom_read_sql(sql, con, *args, **kwargs):
        if hasattr(con, 'is_postgres') and con.is_postgres:
            sql = sql.replace('?', '%s')
            sql = sql.replace('is_active = 1', 'is_active = TRUE')
            sql = sql.replace('is_active = 0', 'is_active = FALSE')
            return pd._original_read_sql_saved(sql, con.conn, *args, **kwargs)
        return pd._original_read_sql_saved(sql, con, *args, **kwargs)
    pd.read_sql = custom_read_sql
    pd._custom_read_sql_installed = True

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
        self.lastrowid = None

    def execute(self, sql, params=()):
        sql = sql.replace('?', '%s')
        sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        sql = sql.replace('DATETIME DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        sql = sql.replace('BOOLEAN DEFAULT 1', 'BOOLEAN DEFAULT TRUE')
        sql = sql.replace('is_active = 1', 'is_active = TRUE')
        sql = sql.replace('is_active = 0', 'is_active = FALSE')
        
        if "INSERT OR IGNORE INTO vendors" in sql:
            sql = "INSERT INTO vendors (name) VALUES (%s) ON CONFLICT (name) DO NOTHING"
            
        try:
            self.cursor.execute(sql, params)
        except Exception as e:
            err_type = type(e).__name__
            if "UniqueViolation" in err_type:
                raise sqlite3.IntegrityError(str(e))
            elif err_type in ["DuplicateColumn", "UndefinedColumn", "InFailedSqlTransaction"]:
                raise sqlite3.OperationalError(str(e))
            else:
                raise e
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

class PostgresConnWrapper:
    def __init__(self, conn, pool=None):
        self.conn = conn
        self.pool = pool
        self.is_postgres = True

    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor())

    def execute(self, sql, params=()):
        c = self.cursor()
        c.execute(sql, params)
        return c

    def commit(self):
        self.conn.commit()

    def close(self):
        if self.pool:
            self.pool.putconn(self.conn)
        else:
            self.conn.close()

DB_FILE = 'bingo_2026.db'

@st.cache_resource
def get_db_pool():
    if "connections" in st.secrets and "postgresql" in st.secrets["connections"]:
        from psycopg2.pool import ThreadedConnectionPool
        url = st.secrets["connections"]["postgresql"]["url"]
        return ThreadedConnectionPool(1, 15, dsn=url)
    elif "postgres" in st.secrets:
        from psycopg2.pool import ThreadedConnectionPool
        url = st.secrets["postgres"]["url"]
        return ThreadedConnectionPool(1, 15, dsn=url)
    return None

def get_conn():
    pool = get_db_pool()
    if pool is not None:
        conn = pool.getconn()
        return PostgresConnWrapper(conn, pool)
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            event_id INTEGER,
            key TEXT,
            value REAL,
            PRIMARY KEY (event_id, key)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS event_vendors (
            event_id INTEGER,
            vendor_id INTEGER,
            troco_enviado REAL DEFAULT 0,
            troco_devolvido REAL DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            PRIMARY KEY (event_id, vendor_id)
        )
    ''')
    conn.commit()
    try:
        c.execute('ALTER TABLE event_vendors ADD COLUMN is_active BOOLEAN DEFAULT 1')
        conn.commit()
    except sqlite3.OperationalError:
        if hasattr(conn, 'is_postgres'):
            conn.conn.rollback()

    c.execute('''
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            round_type TEXT,
            name TEXT,
            valor_cartela REAL,
            UNIQUE(event_id, round_type, name)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendor_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER,
            vendor_id INTEGER,
            cartelas_recebidas INTEGER DEFAULT 0,
            cartelas_adicionais INTEGER DEFAULT 0,
            cartelas_devolvidas INTEGER DEFAULT 0,
            val_dinheiro REAL DEFAULT 0,
            val_pix REAL DEFAULT 0,
            val_santa_ficha REAL DEFAULT 0,
            val_debito REAL DEFAULT 0,
            UNIQUE(round_id, vendor_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sangrias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            valor REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    try:
        c.execute("ALTER TABLE audit_logs ADD COLUMN username TEXT DEFAULT 'Sistema'")
        conn.commit()
    except sqlite3.OperationalError:
        if hasattr(conn, 'is_postgres'):
            conn.conn.rollback()
    conn.close()
