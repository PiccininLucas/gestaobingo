import psycopg2
import toml
import sqlite3

# Simular o comportamento do app.py para o banco de dados
class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
    def execute(self, sql, params=()):
        sql = sql.replace('?', '%s')
        sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        sql = sql.replace('DATETIME DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        sql = sql.replace('BOOLEAN DEFAULT 1', 'BOOLEAN DEFAULT TRUE')
        if "INSERT OR IGNORE INTO vendors" in sql:
            sql = "INSERT INTO vendors (name) VALUES (%s) ON CONFLICT (name) DO NOTHING"
        self.cursor.execute(sql, params)
        return self
    def fetchone(self): return self.cursor.fetchone()
    def fetchall(self): return self.cursor.fetchall()

class PostgresConnWrapper:
    def __init__(self, conn):
        self.conn = conn
        self.is_postgres = True
    def cursor(self): return PostgresCursorWrapper(self.conn.cursor())
    def execute(self, sql, params=()):
        c = self.cursor()
        c.execute(sql, params)
        return c
    def commit(self): self.conn.commit()
    def close(self): self.conn.close()

def run_init():
    secrets = toml.load('c:/Projetos/GestaoBingoLocal/.streamlit/secrets.toml')
    url = secrets['connections']['postgresql']['url']
    raw_conn = psycopg2.connect(url)
    conn = PostgresConnWrapper(raw_conn)
    c = conn.cursor()
    
    print("Criando tabelas...")
    queries = [
        '''CREATE TABLE IF NOT EXISTS events (id SERIAL PRIMARY KEY, name TEXT UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
        '''CREATE TABLE IF NOT EXISTS settings (event_id INTEGER, key TEXT, value REAL, PRIMARY KEY (event_id, key))''',
        '''CREATE TABLE IF NOT EXISTS vendors (id SERIAL PRIMARY KEY, name TEXT UNIQUE)''',
        '''CREATE TABLE IF NOT EXISTS event_vendors (event_id INTEGER, vendor_id INTEGER, troco_enviado REAL DEFAULT 0, troco_devolvido REAL DEFAULT 0, is_active BOOLEAN DEFAULT TRUE, PRIMARY KEY (event_id, vendor_id))''',
        '''CREATE TABLE IF NOT EXISTS rounds (id SERIAL PRIMARY KEY, event_id INTEGER, round_type TEXT, name TEXT, valor_cartela REAL, UNIQUE(event_id, round_type, name))''',
        '''CREATE TABLE IF NOT EXISTS vendor_rounds (id SERIAL PRIMARY KEY, round_id INTEGER, vendor_id INTEGER, cartelas_recebidas INTEGER DEFAULT 0, cartelas_adicionais INTEGER DEFAULT 0, cartelas_devolvidas INTEGER DEFAULT 0, val_dinheiro REAL DEFAULT 0, val_pix REAL DEFAULT 0, val_santa_ficha REAL DEFAULT 0, val_debito REAL DEFAULT 0, UNIQUE(round_id, vendor_id))''',
        '''CREATE TABLE IF NOT EXISTS sangrias (id SERIAL PRIMARY KEY, event_id INTEGER, valor REAL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
        '''CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, event_id INTEGER, action TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, username TEXT DEFAULT 'Sistema')'''
    ]
    
    for q in queries:
        c.execute(q)
    
    conn.commit()
    print("Tabelas criadas/verificadas.")
    
    # Verificar tabelas
    c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
    tables = [row[0] for row in c.fetchall()]
    print(f"Tabelas no Supabase: {', '.join(tables)}")
    
    conn.close()

if __name__ == "__main__":
    run_init()
