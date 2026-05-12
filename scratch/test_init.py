import sys
import os
from unittest import mock
import toml

# Adicionar o diretório do projeto ao path
sys.path.append('c:/Projetos/GestaoBingoLocal')

# Carregar secrets
with open('c:/Projetos/GestaoBingoLocal/.streamlit/secrets.toml', 'r') as f:
    secrets_data = toml.load(f)

# Mock Streamlit ANTES de importar app.py
st_mock = mock.Mock()
st_mock.secrets = secrets_data
st_mock.session_state = {"password_correct": True, "logged_user": "admin"}
st_mock.cache_resource = lambda x: x 

def mock_dialog(title):
    return lambda x: x
st_mock.dialog = mock_dialog

# Forçar o mock no sys.modules
sys.modules['streamlit'] = st_mock

try:
    import app
    print("Iniciando init_db()...")
    app.init_db()
    print("init_db() concluído.")
    
    # Verificar tabelas novamente
    conn = app.get_conn()
    cur = conn.conn.cursor() 
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
    tables = [row[0] for row in cur.fetchall()]
    print(f"Tabelas no banco agora: {', '.join(tables)}")
    conn.close()
    
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
