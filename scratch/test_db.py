import psycopg2
import toml
import os

def test_connection():
    try:
        # Carregar secrets
        secrets_path = 'c:/Projetos/GestaoBingoLocal/.streamlit/secrets.toml'
        if not os.path.exists(secrets_path):
            print(f"ERRO: Arquivo {secrets_path} não encontrado.")
            return

        secrets = toml.load(secrets_path)
        url = secrets.get('connections', {}).get('postgresql', {}).get('url')
        
        if not url:
            print("ERRO: URL do PostgreSQL não encontrada no secrets.toml.")
            return

        print(f"Tentando conectar ao Supabase...")
        conn = psycopg2.connect(url)
        print("CONEXÃO ESTABELECIDA COM SUCESSO!")
        
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"Versão do Banco: {version[0]}")
        
        # Testar se as tabelas existem (rodar parte do init_db)
        print("Verificando tabelas do Bingo...")
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [row[0] for row in cur.fetchall()]
        print(f"Tabelas encontradas: {', '.join(tables) if tables else 'Nenhuma'}")
        
        cur.close()
        conn.close()
        print("\nTeste concluído com sucesso!")

    except Exception as e:
        print(f"ERRO DURANTE O TESTE: {e}")

if __name__ == "__main__":
    test_connection()
