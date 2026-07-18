import psycopg2
from datetime import date, timedelta
from config import DB_CONFIG

# ── CONEXIÓN ─────────────────────────────────────────────────
def conectar():
    return psycopg2.connect(**DB_CONFIG)

# ── 1. DIM_FECHA ─────────────────────────────────────────────
def cargar_dim_fecha(conn):
    print("Cargando dim_fecha...")
    cursor = conn.cursor()

    dias_semana = {
        0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
        3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
    }

    inicio = date(2018, 1, 1)
    fin    = date(2045, 12, 31)
    fechas = []

    actual = inicio
    while actual <= fin:
        fechas.append((
            actual,
            actual.year,
            actual.month,
            (actual.month - 1) // 3 + 1,
            dias_semana[actual.weekday()],
            actual.weekday() >= 5
        ))
        actual += timedelta(days=1)

    cursor.executemany("""
        INSERT INTO dw.dim_fecha
            (fecha, anio, mes, trimestre, dia_semana, es_fin_semana)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (fecha) DO NOTHING
    """, fechas)

    conn.commit()
    cursor.close()
    print(f"{len(fechas):,} fechas cargadas")

# ── 2. DIM_CANAL ─────────────────────────────────────────────
def cargar_dim_canal(conn):
    print("Cargando dim_canal...")
    cursor = conn.cursor()

    cursor.execute("SELECT canal_id, nombre FROM oltp.canal")
    canales = cursor.fetchall()

    cursor.executemany("""
        INSERT INTO dw.dim_canal (canal_id, nombre)
        VALUES (%s,%s)
        ON CONFLICT (canal_id) DO NOTHING
    """, canales)

    conn.commit()
    cursor.close()
    print(f"{len(canales)} canales cargados")

# ── 3. DIM_AGENCIA ────────────────────────────────────────────
def cargar_dim_agencia(conn):
    print("Cargando dim_agencia...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT agencia_id, nombre, ciudad, distrito, es_virtual
        FROM oltp.agencia
    """)
    agencias = cursor.fetchall()

    cursor.executemany("""
        INSERT INTO dw.dim_agencia
            (agencia_id, nombre, ciudad, distrito, es_virtual)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (agencia_id) DO NOTHING
    """, agencias)

    conn.commit()
    cursor.close()
    print(f"{len(agencias)} agencias cargadas")

# ── 4. DIM_PRODUCTO ───────────────────────────────────────────
def cargar_dim_producto(conn):
    print("Cargando dim_producto...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT producto_id, nombre, categoria,
               comision_pct, costo_fondeo_pct
        FROM oltp.producto
    """)
    productos = cursor.fetchall()

    cursor.executemany("""
        INSERT INTO dw.dim_producto
            (producto_id, nombre, categoria, comision_pct, costo_fondeo_pct)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (producto_id) DO NOTHING
    """, productos)

    conn.commit()
    cursor.close()
    print(f"{len(productos)} productos cargados")

# ── 5. DIM_CLIENTE ────────────────────────────────────────────
def cargar_dim_cliente(conn):
    print("Cargando dim_cliente...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            cliente_id,
            nombre || ' ' || apellido          AS nombre_completo,
            DATE_PART('year', AGE(fecha_nacimiento))::INT AS edad,
            sexo,
            estado_civil,
            profesion,
            ingreso_mensual,
            ciudad,
            fecha_registro,
            DATE_PART('year', AGE(fecha_registro)) * 12 +
            DATE_PART('month', AGE(fecha_registro))
                                               AS antiguedad_meses
        FROM oltp.cliente
    """)
    clientes = cursor.fetchall()

    rows = []
    for row in clientes:
        (cliente_id, nombre_completo, edad, sexo, estado_civil,
         profesion, ingreso_mensual, ciudad, fecha_registro,
         antiguedad_meses) = row
        rows.append((
            cliente_id,
            nombre_completo,
            int(edad),
            sexo,
            estado_civil,
            profesion,
            float(ingreso_mensual),
            ciudad,
            None,           # segmento_rfm — se llena en Fase 6
            int(antiguedad_meses),
            fecha_registro
        ))

    cursor.executemany("""
        INSERT INTO dw.dim_cliente
            (cliente_id, nombre_completo, edad, sexo, estado_civil,
             profesion, ingreso_mensual, ciudad, segmento_rfm,
             antiguedad_meses, fecha_registro)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (cliente_id) DO NOTHING
    """, rows)

    conn.commit()
    cursor.close()
    print(f"{len(rows):,} clientes cargados")

# ── HELPER: obtener fecha_sk ──────────────────────────────────
def get_fecha_sk(cursor, fecha):
    """Devuelve el fecha_sk para una fecha dada."""
    if fecha is None:
        return None
    if hasattr(fecha, 'date'):
        fecha = fecha.date()
    cursor.execute(
        "SELECT fecha_sk FROM dw.dim_fecha WHERE fecha = %s", (fecha,)
    )
    row = cursor.fetchone()
    return row[0] if row else None

# ── HELPER: obtener surrogate keys ───────────────────────────
def build_maps(conn):
    """Construye mapas de claves naturales a surrogate keys."""
    cursor = conn.cursor()

    cursor.execute("SELECT cliente_id, cliente_sk FROM dw.dim_cliente")
    cliente_map = {r[0]: r[1] for r in cursor.fetchall()}

    cursor.execute("SELECT producto_id, producto_sk FROM dw.dim_producto")
    producto_map = {r[0]: r[1] for r in cursor.fetchall()}

    cursor.execute("SELECT canal_id, canal_sk FROM dw.dim_canal")
    canal_map = {r[0]: r[1] for r in cursor.fetchall()}

    cursor.execute("SELECT agencia_id, agencia_sk FROM dw.dim_agencia")
    agencia_map = {r[0]: r[1] for r in cursor.fetchall()}

    cursor.execute("SELECT fecha, fecha_sk FROM dw.dim_fecha")
    fecha_map = {r[0]: r[1] for r in cursor.fetchall()}

    cursor.close()
    return cliente_map, producto_map, canal_map, agencia_map, fecha_map

# ── 6. FACT_TRANSACCIONES ─────────────────────────────────────
def cargar_fact_transacciones(conn):
    print("Cargando fact_transacciones...")
    cursor = conn.cursor()

    cliente_map, producto_map, canal_map, agencia_map, fecha_map = build_maps(conn)

    cursor.execute("""
        SELECT
            t.transaccion_id,
            c.cliente_id,
            t.fecha::DATE,
            t.producto_id,
            t.canal_id,
            t.agencia_id,
            t.tipo_transaccion,
            t.monto,
            p.comision_pct
        FROM oltp.transaccion t
        JOIN oltp.cuenta   c ON c.cuenta_id   = t.cuenta_id
        JOIN oltp.producto p ON p.producto_id  = t.producto_id
    """)
    transacciones = cursor.fetchall()

    batch = []
    for row in transacciones:
        (transaccion_id, cliente_id, fecha, producto_id,
         canal_id, agencia_id, tipo, monto, comision_pct) = row

        monto        = float(monto)
        comision_pct = float(comision_pct)
        ingreso_com  = round(monto * comision_pct, 2)

        batch.append((
            transaccion_id,
            cliente_map[cliente_id],
            fecha_map.get(fecha),
            producto_map[producto_id],
            canal_map[canal_id],
            agencia_map[agencia_id],
            tipo,
            monto,
            ingreso_com
        ))

        if len(batch) >= 2000:
            cursor.executemany("""
                INSERT INTO dw.fact_transacciones
                    (transaccion_id, cliente_sk, fecha_sk, producto_sk,
                     canal_sk, agencia_sk, tipo_transaccion, monto, ingreso_comision)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (transaccion_id) DO NOTHING
            """, batch)
            conn.commit()
            batch = []

    if batch:
        cursor.executemany("""
            INSERT INTO dw.fact_transacciones
                (transaccion_id, cliente_sk, fecha_sk, producto_sk,
                 canal_sk, agencia_sk, tipo_transaccion, monto, ingreso_comision)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (transaccion_id) DO NOTHING
        """, batch)
        conn.commit()

    cursor.close()
    print(f"{len(transacciones):,} transacciones cargadas")

# ── 7. FACT_PRESTAMOS ─────────────────────────────────────────
def cargar_fact_prestamos(conn):
    print("Cargando fact_prestamos...")
    cursor = conn.cursor()

    cliente_map, producto_map, _, _, fecha_map = build_maps(conn)

    cursor.execute("""
        SELECT
            pr.prestamo_id,
            pr.cliente_id,
            pr.fecha_desembolso,
            pr.producto_id,
            pr.monto,
            pr.tasa_interes,
            pr.plazo_meses,
            p.costo_fondeo_pct,
            COALESCE(MAX(pa.dias_mora), 0) AS max_dias_mora
        FROM oltp.prestamo pr
        JOIN oltp.producto p  ON p.producto_id  = pr.producto_id
        LEFT JOIN oltp.pago pa ON pa.prestamo_id = pr.prestamo_id
        GROUP BY pr.prestamo_id, pr.cliente_id, pr.fecha_desembolso,
                 pr.producto_id, pr.monto, pr.tasa_interes,
                 pr.plazo_meses, p.costo_fondeo_pct
    """)
    prestamos = cursor.fetchall()

    rows = []
    for row in prestamos:
        (prestamo_id, cliente_id, fecha_desembolso, producto_id,
         monto, tasa, plazo, costo_fondeo_pct, max_dias_mora) = row

        monto            = float(monto)
        tasa             = float(tasa)
        costo_fondeo_pct = float(costo_fondeo_pct)
        max_dias_mora    = int(max_dias_mora)

        # Fórmulas documentadas en Fase 2 regla 21 y 22
        ingreso_estimado      = round(monto * tasa * (plazo / 12), 2)
        costo_fondeo_estimado = round(monto * costo_fondeo_pct * (plazo / 12), 2)
        margen_estimado       = round(ingreso_estimado - costo_fondeo_estimado, 2)
        es_default            = max_dias_mora > 90

        rows.append((
            prestamo_id,
            cliente_map[cliente_id],
            fecha_map.get(fecha_desembolso),
            producto_map[producto_id],
            monto,
            tasa,
            plazo,
            ingreso_estimado,
            costo_fondeo_estimado,
            None,            # score_riesgo — se llena en Fase 6
            max_dias_mora,
            es_default,
            margen_estimado
        ))

    cursor.executemany("""
        INSERT INTO dw.fact_prestamos
            (prestamo_id, cliente_sk, fecha_sk, producto_sk,
             monto, tasa_interes, plazo_meses,
             ingreso_estimado, costo_fondeo_estimado,
             score_riesgo, max_dias_mora, es_default, margen_estimado)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (prestamo_id) DO NOTHING
    """, rows)

    conn.commit()
    cursor.close()
    print(f"{len(rows):,} préstamos cargados")

# ── 8. FACT_PAGOS ─────────────────────────────────────────────
def cargar_fact_pagos(conn):
    print("Cargando fact_pagos...")
    cursor = conn.cursor()

    _, _, _, _, fecha_map = build_maps(conn)

    cursor.execute("""
        SELECT pago_id, prestamo_id, fecha_programada,
               dias_mora, estado_pago
        FROM oltp.pago
    """)
    pagos = cursor.fetchall()

    batch = []
    for row in pagos:
        pago_id, prestamo_id, fecha_prog, dias_mora, estado_pago = row
        fecha_sk = fecha_map.get(fecha_prog)
        if fecha_sk is None:
            continue # saltar cuotas sin fecha_sk
        batch.append((
            pago_id,
            prestamo_id,
            fecha_sk,
            int(dias_mora),
            estado_pago
        ))

        if len(batch) >= 2000:
            cursor.executemany("""
                INSERT INTO dw.fact_pagos
                    (pago_id, prestamo_id, fecha_sk, dias_mora, estado_pago)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (pago_id) DO NOTHING
            """, batch)
            conn.commit()
            batch = []

    if batch:
        cursor.executemany("""
            INSERT INTO dw.fact_pagos
                (pago_id, prestamo_id, fecha_sk, dias_mora, estado_pago)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (pago_id) DO NOTHING
        """, batch)
        conn.commit()

    cursor.close()
    print(f"{len(pagos):,} pagos cargados")

# ── 9. FACT_PRODUCTOS_CONTRATADOS ─────────────────────────────
def cargar_fact_productos_contratados(conn):
    print("Cargando fact_productos_contratados...")
    cursor = conn.cursor()

    cliente_map, producto_map, _, _, fecha_map = build_maps(conn)

    # Tarjetas
    cursor.execute("""
        SELECT cliente_id, producto_id, fecha_emision,
               limite_credito, estado
        FROM oltp.tarjeta
    """)
    tarjetas = cursor.fetchall()

    rows = []
    for cliente_id, producto_id, fecha_emision, limite, estado in tarjetas:
        rows.append((
            cliente_map[cliente_id],
            fecha_map.get(fecha_emision),
            producto_map[producto_id],
            'Tarjeta',
            float(limite) if limite else 0.0,
            estado
        ))

    # Seguros
    cursor.execute("""
        SELECT cliente_id, producto_id, fecha_inicio,
               prima_mensual, estado
        FROM oltp.seguro
    """)
    seguros = cursor.fetchall()

    for cliente_id, producto_id, fecha_inicio, prima, estado in seguros:
        rows.append((
            cliente_map[cliente_id],
            fecha_map.get(fecha_inicio),
            producto_map[producto_id],
            'Seguro',
            float(prima),
            estado
        ))

    cursor.executemany("""
        INSERT INTO dw.fact_productos_contratados
            (cliente_sk, fecha_sk, producto_sk,
             tipo_producto, monto_referencia, estado)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, rows)

    conn.commit()
    cursor.close()
    print(f"{len(rows):,} productos contratados cargados")

# ── RESUMEN FINAL ─────────────────────────────────────────────
def resumen(conn):
    cursor = conn.cursor()
    tablas = [
        ('dw.dim_fecha',                  'dim_fecha'),
        ('dw.dim_cliente',                'dim_cliente'),
        ('dw.dim_producto',               'dim_producto'),
        ('dw.dim_canal',                  'dim_canal'),
        ('dw.dim_agencia',                'dim_agencia'),
        ('dw.fact_transacciones',         'fact_transacciones'),
        ('dw.fact_prestamos',             'fact_prestamos'),
        ('dw.fact_pagos',                 'fact_pagos'),
        ('dw.fact_productos_contratados', 'fact_productos_contratados'),
    ]
    print("\n── Resumen Data Warehouse ──────────────────────")
    for tabla, nombre in tablas:
        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
        n = cursor.fetchone()[0]
        print(f"  {nombre:<35} {n:>10,} registros")
    print("────────────────────────────────────────────────")
    cursor.close()

# ── EJECUCIÓN PRINCIPAL ───────────────────────────────────────
if __name__ == '__main__':
    print("=== Customer 360 — ETL: Modelo A → Modelo B ===\n")
    conn = conectar()
    try:
        cargar_dim_fecha(conn)
        cargar_dim_canal(conn)
        cargar_dim_agencia(conn)
        cargar_dim_producto(conn)
        cargar_dim_cliente(conn)
        cargar_fact_transacciones(conn)
        cargar_fact_prestamos(conn)
        cargar_fact_pagos(conn)
        cargar_fact_productos_contratados(conn)
        resumen(conn)
        print("\nETL completo.")
    except Exception as e:
        conn.rollback()
        print(f"\n Error: {e}")
        raise
    finally:
        conn.close()