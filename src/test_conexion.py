import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM oltp.canal")
    resultado = cursor.fetchone()
    print(f"Conexión exitosa — Canales en BD: {resultado[0]}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error de conexión: {e}")