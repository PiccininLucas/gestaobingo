import psycopg2
import toml

def check_data():
    secrets = toml.load('c:/Projetos/GestaoBingoLocal/.streamlit/secrets.toml')
    url = secrets['connections']['postgresql']['url']
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM events;")
    events = cur.fetchall()
    print("Eventos no BD:", events)
    
    cur.execute("SELECT * FROM vendors;")
    vendors = cur.fetchall()
    print("Vendedores no BD:", vendors)
    
    cur.execute("SELECT * FROM audit_logs;")
    logs = cur.fetchall()
    print("Logs no BD:", logs)
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_data()
