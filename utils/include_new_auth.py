import uuid
import bcrypt
import psycopg2
import os
from datetime import datetime

# Configurações de conexão
DB_CONFIG = {
    'host': '#',
    'port': 5432,
    'user': '#',
    'password': '#',
    'dbname': '#'
}

# Empresas e usuários a serem inseridos exemplo
usuarios = [
   # {"username": "empresa", "email": "empresa@empresa.com", "password": "##", "company": "empresa"}
]

# Função para hash da senha
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Conexão com o banco
try:
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    for user in usuarios:
        user_id = str(uuid.uuid4())
        password_hash = hash_password(user["password"])
        now = datetime.now().isoformat()

        insert_query = """
        INSERT INTO security.users (
            id, username, email, password_hash, company, created_at, updated_at, is_active
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
        """

        cur.execute(insert_query, (
            user_id,
            user["username"],
            user["email"],
            password_hash,
            user["company"],
            now,
            now
        ))
        print(f"Usuário {user['username']} inserido com sucesso.")

    cur.close()
    conn.close()

except Exception as e:
    print("Erro ao conectar ou inserir:", e)
