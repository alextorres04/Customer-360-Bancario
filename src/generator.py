import random
import numpy as np
from faker import Faker
from datetime import date, timedelta
import psycopg2
from config import DB_CONFIG

fake = Faker('es_ES')
random.seed(42)
np.random.seed(42)

# ── CONFIGURACIÓN DE VOLUMEN ──────────────────────────────────
N_CLIENTES      = 5000
N_TRANSACCIONES = 150000

# ── CONEXIÓN ─────────────────────────────────────────────────
def conectar():
    return psycopg2.connect(**DB_CONFIG)

# ── UTILIDADES ────────────────────────────────────────────────
def fecha_aleatoria(inicio, fin):
    delta = (fin - inicio).days
    if delta <= 0:
        return inicio
    return inicio + timedelta(days=random.randint(0, delta))

def fecha_aleatoria_sesgada(inicio, fin, sesgo='reciente'):
    dias = (fin - inicio).days
    if dias <= 0:
        return inicio
    if sesgo == 'reciente':
        d = int(np.random.beta(2, 1) * dias)
    else:
        d = int(np.random.beta(1, 2) * dias)
    return inicio + timedelta(days=d)

# ── 1. CLIENTES ───────────────────────────────────────────────
def generar_clientes(conn):
    print("Generando clientes...")
    cursor = conn.cursor()

    ciudades = [
        'Lima', 'Lima', 'Lima', 'Lima',
        'Arequipa', 'Trujillo', 'Chiclayo',
        'Piura', 'Cusco', 'Iquitos', 'Huancayo'
    ]
    profesiones = [
        'Ingeniero', 'Médico', 'Abogado', 'Contador', 'Docente',
        'Comerciante', 'Empresario', 'Enfermero', 'Arquitecto',
        'Economista', 'Administrador', 'Técnico', 'Independiente'
    ]

    hoy = date.today()
    fecha_inicio_banco = date(2018, 1, 1)

    clientes = []
    for _ in range(N_CLIENTES):
        edad = random.randint(18, 75)
        fecha_nac = hoy - timedelta(days=edad * 365 + random.randint(0, 364))
        fecha_reg = fecha_aleatoria(fecha_inicio_banco, hoy - timedelta(days=30))

        sexo = random.choice(['M', 'F'])
        nombre = fake.first_name_male() if sexo == 'M' else fake.first_name_female()

        # float desde el inicio para evitar Decimal
        ingreso = float(round(max(500, np.random.lognormal(mean=7.5, sigma=0.6)), 2))

        clientes.append((
            nombre,
            fake.last_name(),
            fecha_nac,
            sexo,
            random.choice(['Soltero', 'Casado', 'Divorciado', 'Viudo', 'Conviviente']),
            random.choice(profesiones),
            ingreso,
            random.choice(ciudades),
            fecha_reg
        ))

    cursor.executemany("""
        INSERT INTO oltp.cliente
            (nombre, apellido, fecha_nacimiento, sexo, estado_civil,
             profesion, ingreso_mensual, ciudad, fecha_registro)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, clientes)

    conn.commit()
    cursor.close()
    print(f"  5000 clientes insertados")

# ── 2. CUENTAS ────────────────────────────────────────────────
def generar_cuentas(conn):
    print("Generando cuentas...")
    cursor = conn.cursor()

    productos_cuenta = [1, 2, 3]
    hoy = date.today()

    cursor.execute("SELECT cliente_id, fecha_registro, ingreso_mensual FROM oltp.cliente")
    clientes = cursor.fetchall()

    cuentas = []
    for cliente_id, fecha_reg, ingreso in clientes:
        ingreso = float(ingreso)
        n_cuentas = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
        productos_usados = random.sample(productos_cuenta, min(n_cuentas, 3))

        for prod_id in productos_usados:
            fecha_apertura = fecha_aleatoria(fecha_reg, hoy - timedelta(days=10))
            saldo = round(max(0, ingreso * random.uniform(0.5, 8) +
                              np.random.normal(0, ingreso * 0.3)), 2)

            limite_inactivo = hoy - timedelta(days=91)
            limite_cerrada  = hoy - timedelta(days=180)

            r = random.random()
            if r < 0.15:
                if fecha_apertura < limite_inactivo:
                    ultimo_mov = fecha_aleatoria(fecha_apertura, limite_inactivo)
                    estado = 'Inactiva'
                else:
                    ultimo_mov = fecha_apertura
                    estado = 'Activa'
            elif r < 0.20:
                if fecha_apertura < limite_cerrada:
                    ultimo_mov = fecha_aleatoria(fecha_apertura, limite_cerrada)
                else:
                    ultimo_mov = fecha_apertura
                estado = 'Cerrada'
            else:
                fecha_desde = max(fecha_apertura, hoy - timedelta(days=89))
                ultimo_mov  = fecha_aleatoria(fecha_desde, hoy)
                estado = 'Activa'

            cuentas.append((
                cliente_id, prod_id,
                random.choice(['Ahorro', 'Corriente', 'Plazo Fijo']),
                saldo, fecha_apertura, ultimo_mov, estado
            ))

    cursor.executemany("""
        INSERT INTO oltp.cuenta
            (cliente_id, producto_id, tipo_cuenta, saldo,
             fecha_apertura, fecha_ultimo_movimiento, estado)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, cuentas)

    conn.commit()
    cursor.close()
    print(f"  {len(cuentas)} cuentas insertadas")

# ── 3. TARJETAS ───────────────────────────────────────────────
def generar_tarjetas(conn):
    print("Generando tarjetas...")
    cursor = conn.cursor()

    cursor.execute("SELECT cliente_id, fecha_registro, ingreso_mensual FROM oltp.cliente")
    clientes = cursor.fetchall()
    hoy = date.today()

    tarjetas = []
    for cliente_id, fecha_reg, ingreso in clientes:
        ingreso = float(ingreso)

        if random.random() < 0.80:
            fecha_emision = fecha_aleatoria(fecha_reg, hoy - timedelta(days=10))
            tarjetas.append((
                cliente_id, 4, 'Débito', None,
                fecha_emision,
                random.choices(['Activa', 'Bloqueada', 'Cancelada'], weights=[85, 10, 5])[0]
            ))

        if random.random() < 0.45:
            prod_id = random.choices([5, 6], weights=[70, 30])[0]
            limite  = round(ingreso * random.uniform(2, 6), 2)
            fecha_emision = fecha_aleatoria(fecha_reg, hoy - timedelta(days=10))
            tarjetas.append((
                cliente_id, prod_id, 'Crédito', limite,
                fecha_emision,
                random.choices(['Activa', 'Bloqueada', 'Cancelada'], weights=[80, 12, 8])[0]
            ))

    cursor.executemany("""
        INSERT INTO oltp.tarjeta
            (cliente_id, producto_id, tipo, limite_credito,
             fecha_emision, estado)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, tarjetas)

    conn.commit()
    cursor.close()
    print(f"  {len(tarjetas)} tarjetas insertadas")

# ── 4. PRÉSTAMOS ──────────────────────────────────────────────
def generar_prestamos(conn):
    print("Generando préstamos...")
    cursor = conn.cursor()

    productos_prestamo = {
        7: {'min': 1000,  'max': 50000,  'tasas': (0.12, 0.28), 'plazos': [12, 24, 36, 48, 60]},
        8: {'min': 10000, 'max': 120000, 'tasas': (0.09, 0.18), 'plazos': [24, 36, 48, 60, 72]},
        9: {'min': 50000, 'max': 400000, 'tasas': (0.07, 0.12), 'plazos': [60, 120, 180, 240]},
    }

    cursor.execute("SELECT cliente_id, fecha_registro, ingreso_mensual FROM oltp.cliente")
    clientes = cursor.fetchall()
    hoy = date.today()

    prestamos = []
    for cliente_id, fecha_reg, ingreso in clientes:
        ingreso = float(ingreso)

        if random.random() > 0.70:
            continue

        n_prestamos = random.choices([1, 2], weights=[75, 25])[0]
        prods = random.choices(list(productos_prestamo.keys()), k=n_prestamos)

        for prod_id in prods:
            cfg    = productos_prestamo[prod_id]
            minimo = cfg['min']
            tope   = max(minimo * 1.5, min(cfg['max'], ingreso * 24))
            monto  = round(random.uniform(minimo, tope), 2)
            tasa   = round(random.uniform(*cfg['tasas']), 4)
            plazo  = random.choice(cfg['plazos'])
            fecha_desembolso = fecha_aleatoria(fecha_reg, hoy - timedelta(days=30))
            estado = random.choices(
                ['Vigente', 'Pagado', 'Castigado'], weights=[65, 30, 5]
            )[0]

            prestamos.append((
                cliente_id, prod_id, monto, tasa, plazo,
                None, fecha_desembolso, estado
            ))

    cursor.executemany("""
        INSERT INTO oltp.prestamo
            (cliente_id, producto_id, monto, tasa_interes, plazo_meses,
             score_riesgo, fecha_desembolso, estado)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, prestamos)

    conn.commit()
    cursor.close()
    print(f"  {len(prestamos)} préstamos insertados")

# ── 5. PAGOS ─────────────────────────────────────────────────
def generar_pagos(conn):
    print("Generando pagos...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT prestamo_id, monto, tasa_interes, plazo_meses,
               fecha_desembolso, estado
        FROM oltp.prestamo
    """)
    prestamos = cursor.fetchall()
    hoy = date.today()

    pagos = []
    for prestamo_id, monto, tasa, plazo, fecha_desembolso, estado in prestamos:
        monto = float(monto)
        tasa  = float(tasa)

        tasa_mensual = tasa / 12
        if tasa_mensual > 0:
            cuota = monto * (tasa_mensual * (1 + tasa_mensual) ** plazo) / \
                    ((1 + tasa_mensual) ** plazo - 1)
        else:
            cuota = monto / plazo
        cuota = round(cuota, 2)

        perfil = random.choices(['alto', 'medio', 'bajo'], weights=[10, 20, 70])[0]

        for n in range(1, plazo + 1):
            fecha_prog = fecha_desembolso + timedelta(days=30 * n)

            if fecha_prog > hoy:
                pagos.append((prestamo_id, n, fecha_prog, None, cuota, 0, 0, 'Vigente'))
                continue

            if estado == 'Castigado':
                if n <= plazo // 3:
                    dias_mora, monto_pagado, est = 0, cuota, 'Pagado'
                else:
                    dias_mora    = random.randint(91, 365)
                    monto_pagado = round(cuota * random.uniform(0, 0.5), 2)
                    est = 'Vencido'

            elif perfil == 'alto':
                r = random.random()
                if r < 0.30:
                    dias_mora    = random.randint(91, 200)
                    monto_pagado = round(cuota * random.uniform(0, 0.7), 2)
                    est = 'Vencido'
                elif r < 0.55:
                    dias_mora    = random.randint(30, 90)
                    monto_pagado = round(cuota * random.uniform(0.5, 1.0), 2)
                    est = 'Vencido'
                else:
                    dias_mora, monto_pagado, est = 0, cuota, 'Pagado'

            elif perfil == 'medio':
                r = random.random()
                if r < 0.10:
                    dias_mora    = random.randint(91, 150)
                    monto_pagado = round(cuota * random.uniform(0.3, 0.9), 2)
                    est = 'Vencido'
                elif r < 0.30:
                    dias_mora    = random.randint(1, 89)
                    monto_pagado = round(cuota * random.uniform(0.7, 1.0), 2)
                    est = 'Vencido'
                else:
                    dias_mora, monto_pagado, est = 0, cuota, 'Pagado'

            else:
                r = random.random()
                if r < 0.03:
                    dias_mora    = random.randint(91, 120)
                    monto_pagado = round(cuota * random.uniform(0.5, 1.0), 2)
                    est = 'Vencido'
                elif r < 0.12:
                    dias_mora    = random.randint(1, 89)
                    monto_pagado = round(cuota * random.uniform(0.8, 1.0), 2)
                    est = 'Vencido'
                else:
                    dias_mora, monto_pagado, est = 0, cuota, 'Pagado'

            fecha_pago = fecha_prog + timedelta(days=dias_mora) if est == 'Pagado' else None

            pagos.append((
                prestamo_id, n, fecha_prog, fecha_pago,
                cuota, monto_pagado, dias_mora, est
            ))

            if len(pagos) >= 1000:
                cursor.executemany("""
                    INSERT INTO oltp.pago
                        (prestamo_id, numero_cuota, fecha_programada, fecha_pago,
                         monto_programado, monto_pagado, dias_mora, estado_pago)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, pagos)
                conn.commit()
                pagos = []

    if pagos:
        cursor.executemany("""
            INSERT INTO oltp.pago
                (prestamo_id, numero_cuota, fecha_programada, fecha_pago,
                 monto_programado, monto_pagado, dias_mora, estado_pago)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, pagos)
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM oltp.pago")
    total = cursor.fetchone()[0]
    cursor.close()
    print(f"  {total:,} pagos insertados")

# ── 6. TRANSACCIONES ─────────────────────────────────────────
def generar_transacciones(conn):
    print("Generando transacciones...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cuenta_id, cliente_id, producto_id, fecha_apertura, estado
        FROM oltp.cuenta WHERE estado != 'Cerrada'
    """)
    cuentas = cursor.fetchall()

    cursor.execute("SELECT canal_id, nombre FROM oltp.canal")
    canal_map = {nombre: cid for cid, nombre in cursor.fetchall()}

    cursor.execute("SELECT agencia_id, es_virtual FROM oltp.agencia")
    agencias         = cursor.fetchall()
    agencias_fisicas = [aid for aid, virt in agencias if not virt]
    agencia_virtual  = [aid for aid, virt in agencias if virt][0]

    canales_digitales = {canal_map['App'], canal_map['Web'], canal_map['ATM']}
    tipos      = ['Depósito', 'Retiro', 'Transferencia', 'Pago de Servicio', 'Compra']
    pesos_tipo = [25, 20, 20, 20, 15]

    hoy            = date.today()
    batch          = []
    total          = 0
    txn_por_cuenta = max(1, N_TRANSACCIONES // len(cuentas))

    for cuenta_id, cliente_id, prod_id, fecha_apertura, estado in cuentas:
        if total >= N_TRANSACCIONES:
            break

        n_txn = max(1, int(np.random.poisson(txn_por_cuenta)))

        for _ in range(n_txn):
            if total >= N_TRANSACCIONES:
                break

            canal_id = random.choices(
                [canal_map['App'], canal_map['Web'], canal_map['ATM'],
                 canal_map['Agencia'], canal_map['Call Center']],
                weights=[30, 20, 20, 25, 5]
            )[0]

            agencia_id = agencia_virtual if canal_id in canales_digitales \
                         else random.choice(agencias_fisicas)

            fecha_desde = max(fecha_apertura, date(2022, 1, 1))
            fecha_base  = fecha_aleatoria(fecha_desde, hoy)

            if fecha_base.month in [11, 12] and random.random() < 0.40:
                mes = random.choice([11, 12])
                dia = min(fecha_base.day, 28 if mes == 11 else 31)
                fecha_base = fecha_base.replace(month=mes, day=dia)

            fecha_hora = fake.date_time_between(
                start_date=fecha_base, end_date=fecha_base
            )

            tipo = random.choices(tipos, weights=pesos_tipo)[0]
            if tipo in ['Depósito', 'Transferencia']:
                monto = round(max(10, np.random.lognormal(6.5, 0.8)), 2)
            elif tipo == 'Retiro':
                monto = round(max(20, np.random.lognormal(5.5, 0.6)), 2)
            else:
                monto = round(max(5, np.random.lognormal(5.0, 0.9)), 2)

            if random.random() < 0.02:
                monto = round(monto * random.uniform(5, 20), 2)

            batch.append((
                cuenta_id, prod_id, canal_id, agencia_id,
                fecha_hora, monto, tipo
            ))
            total += 1

            if len(batch) >= 2000:
                cursor.executemany("""
                    INSERT INTO oltp.transaccion
                        (cuenta_id, producto_id, canal_id, agencia_id,
                         fecha, monto, tipo_transaccion)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, batch)
                conn.commit()
                batch = []
                print(f"    {total:,} transacciones insertadas...", end='\r')

    if batch:
        cursor.executemany("""
            INSERT INTO oltp.transaccion
                (cuenta_id, producto_id, canal_id, agencia_id,
                 fecha, monto, tipo_transaccion)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, batch)
        conn.commit()

    cursor.close()
    print(f"\n  {total:,} transacciones insertadas")

# ── 7. SEGUROS ────────────────────────────────────────────────
def generar_seguros(conn):
    print("Generando seguros...")
    cursor = conn.cursor()

    tipos_seguro = {
        10: ('Vida',        50,  150),
        11: ('Vehicular',   80,  250),
        12: ('Hogar',       60,  180),
        13: ('Desgravamen', 30,  100),
    }

    cursor.execute("SELECT cliente_id, fecha_registro FROM oltp.cliente")
    clientes = cursor.fetchall()
    hoy = date.today()

    seguros = []
    for cliente_id, fecha_reg in clientes:
        if random.random() > 0.55:
            continue

        n_seguros = random.choices([1, 2], weights=[80, 20])[0]
        prods = random.sample(list(tipos_seguro.keys()), min(n_seguros, 4))

        for prod_id in prods:
            tipo_s, prima_min, prima_max = tipos_seguro[prod_id]
            prima        = round(random.uniform(prima_min, prima_max), 2)
            fecha_inicio = fecha_aleatoria(fecha_reg, hoy - timedelta(days=30))
            estado       = random.choices(
                ['Activo', 'Cancelado', 'Vencido'], weights=[75, 15, 10]
            )[0]

            seguros.append((
                cliente_id, prod_id, tipo_s,
                prima, fecha_inicio, estado
            ))

    cursor.executemany("""
        INSERT INTO oltp.seguro
            (cliente_id, producto_id, tipo_seguro,
             prima_mensual, fecha_inicio, estado)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, seguros)

    conn.commit()
    cursor.close()
    print(f"  {len(seguros)} seguros insertados")

# ── RESUMEN FINAL ─────────────────────────────────────────────
def resumen(conn):
    cursor = conn.cursor()
    tablas = ['cliente', 'cuenta', 'tarjeta', 'prestamo',
              'pago', 'transaccion', 'seguro']
    print("\n── Resumen de datos generados ──────────────────")
    for tabla in tablas:
        cursor.execute(f"SELECT COUNT(*) FROM oltp.{tabla}")
        n = cursor.fetchone()[0]
        print(f"  {tabla:<15} {n:>10,} registros")
    print("────────────────────────────────────────────────")
    cursor.close()

# ── EJECUCIÓN PRINCIPAL ───────────────────────────────────────
if __name__ == '__main__':
    print("=== Customer 360 — Generador de datos sintéticos ===\n")
    conn = conectar()
    try:
        generar_clientes(conn)
        generar_cuentas(conn)
        generar_tarjetas(conn)
        generar_prestamos(conn)
        generar_pagos(conn)
        generar_transacciones(conn)
        generar_seguros(conn)
        resumen(conn)
        print("\nGeneracion completa.")
    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        conn.close()