import psycopg2
import sys
sys.path.append(r'C:\customer360\src')
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

cursor.execute("""
    SELECT COUNT(DISTINCT c.cliente_sk)
    FROM dw.fact_transacciones t
    JOIN dw.dim_fecha f ON f.fecha_sk = t.fecha_sk
    JOIN dw.dim_cliente c ON c.cliente_sk = t.cliente_sk
    WHERE f.fecha >= CURRENT_DATE - 90
""")

print(f"Clientes activos últimos 90 días: {cursor.fetchone()[0]:,}")

cursor.execute("""
    SELECT MIN(fecha), MAX(fecha) 
    FROM dw.dim_fecha f
    JOIN dw.fact_transacciones t ON t.fecha_sk = f.fecha_sk
""")
row = cursor.fetchone()
print(f"Rango de fechas: {row[0]} a {row[1]}")

cursor.close()
conn.close()


conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()
cursor.execute("""
    SELECT fecha_sk FROM dw.dim_fecha 
    WHERE fecha = CURRENT_DATE - 90
""")
print(cursor.fetchone()[0])
cursor.close()
conn.close()