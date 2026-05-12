import sys
import toml
import traceback

sys.path.append('c:/Projetos/GestaoBingoLocal')

try:
    import app
    
    # Simular adicionar evento
    print("Testando insert Evento...")
    conn = app.get_conn()
    conn.execute("INSERT INTO events (name) VALUES (?)", ("Teste Evento 1",))
    conn.commit()
    print("Commit realizado com sucesso.")
    
    c = conn.execute("SELECT * FROM events")
    rows = c.fetchall()
    print("Eventos no DB:", rows)
    
    conn.close()
    
except Exception as e:
    print(f"ERRO: {e}")
    traceback.print_exc()
