-- ============================================================
-- Customer 360 Bancario
-- Fase 3 — Modelo A: Base de datos relacional normalizada (OLTP)
-- ============================================================

-- Esquema dedicado para el modelo OLTP
CREATE SCHEMA IF NOT EXISTS oltp;

-- ── 1. CANAL ─────────────────────────────────────────────────
CREATE TABLE oltp.canal (
    canal_id  SERIAL       PRIMARY KEY,
    nombre    VARCHAR(30)  NOT NULL CHECK (nombre IN ('ATM','App','Web','Agencia','Call Center'))
);

-- ── 2. AGENCIA ───────────────────────────────────────────────
CREATE TABLE oltp.agencia (
    agencia_id  SERIAL       PRIMARY KEY,
    nombre      VARCHAR(60)  NOT NULL,
    ciudad      VARCHAR(60),
    distrito    VARCHAR(60),
    es_virtual  BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_agencia_ciudad
        CHECK (es_virtual = TRUE OR ciudad IS NOT NULL)
);

-- ── 3. CLIENTE ───────────────────────────────────────────────
CREATE TABLE oltp.cliente (
    cliente_id       SERIAL        PRIMARY KEY,
    nombre           VARCHAR(80)   NOT NULL,
    apellido         VARCHAR(80)   NOT NULL,
    fecha_nacimiento DATE          NOT NULL,
    sexo             CHAR(1)       NOT NULL CHECK (sexo IN ('M','F')),
    estado_civil     VARCHAR(20)   NOT NULL CHECK (estado_civil IN ('Soltero','Casado','Divorciado','Viudo','Conviviente')),
    profesion        VARCHAR(80),
    ingreso_mensual  NUMERIC(12,2) NOT NULL CHECK (ingreso_mensual >= 0),
    ciudad           VARCHAR(60),
    fecha_registro   DATE          NOT NULL,
    CONSTRAINT chk_fecha_nacimiento
        CHECK (fecha_nacimiento < fecha_registro)
);

-- ── 4. PRODUCTO ──────────────────────────────────────────────
CREATE TABLE oltp.producto (
    producto_id      SERIAL        PRIMARY KEY,
    nombre           VARCHAR(80)   NOT NULL,
    categoria        VARCHAR(30)   NOT NULL CHECK (categoria IN ('Cuenta','Tarjeta','Préstamo','Seguro')),
    comision_pct     NUMERIC(5,4)  NOT NULL DEFAULT 0 CHECK (comision_pct >= 0),
    costo_fondeo_pct NUMERIC(5,4)  NOT NULL DEFAULT 0 CHECK (costo_fondeo_pct >= 0)
);

-- ── 5. CUENTA ────────────────────────────────────────────────
CREATE TABLE oltp.cuenta (
    cuenta_id               SERIAL        PRIMARY KEY,
    cliente_id              INT           NOT NULL REFERENCES oltp.cliente(cliente_id),
    producto_id             INT           NOT NULL REFERENCES oltp.producto(producto_id),
    tipo_cuenta             VARCHAR(30)   NOT NULL CHECK (tipo_cuenta IN ('Ahorro','Corriente','Plazo Fijo')),
    saldo                   NUMERIC(14,2) NOT NULL DEFAULT 0,
    fecha_apertura          DATE          NOT NULL,
    fecha_ultimo_movimiento DATE,
    estado                  VARCHAR(20)   NOT NULL CHECK (estado IN ('Activa','Inactiva','Cerrada'))
);

-- ── 6. TARJETA ───────────────────────────────────────────────
CREATE TABLE oltp.tarjeta (
    tarjeta_id     SERIAL        PRIMARY KEY,
    cliente_id     INT           NOT NULL REFERENCES oltp.cliente(cliente_id),
    producto_id    INT           NOT NULL REFERENCES oltp.producto(producto_id),
    tipo           VARCHAR(20)   NOT NULL CHECK (tipo IN ('Débito','Crédito')),
    limite_credito NUMERIC(12,2) CHECK (limite_credito IS NULL OR limite_credito > 0),
    fecha_emision  DATE          NOT NULL,
    estado         VARCHAR(20)   NOT NULL CHECK (estado IN ('Activa','Bloqueada','Cancelada')),
    CONSTRAINT chk_limite_credito
        CHECK (tipo = 'Débito' AND limite_credito IS NULL
            OR tipo = 'Crédito' AND limite_credito IS NOT NULL)
);

-- ── 7. PRÉSTAMO ──────────────────────────────────────────────
CREATE TABLE oltp.prestamo (
    prestamo_id      SERIAL        PRIMARY KEY,
    cliente_id       INT           NOT NULL REFERENCES oltp.cliente(cliente_id),
    producto_id      INT           NOT NULL REFERENCES oltp.producto(producto_id),
    monto            NUMERIC(14,2) NOT NULL CHECK (monto > 0),
    tasa_interes     NUMERIC(6,4)  NOT NULL CHECK (tasa_interes > 0),
    plazo_meses      INT           NOT NULL CHECK (plazo_meses > 0),
    score_riesgo     NUMERIC(5,2)  CHECK (score_riesgo BETWEEN 0 AND 100),
    fecha_desembolso DATE          NOT NULL,
    estado           VARCHAR(20)   NOT NULL CHECK (estado IN ('Vigente','Pagado','Castigado'))
);

-- ── 8. PAGO ──────────────────────────────────────────────────
CREATE TABLE oltp.pago (
    pago_id           SERIAL        PRIMARY KEY,
    prestamo_id       INT           NOT NULL REFERENCES oltp.prestamo(prestamo_id),
    numero_cuota      INT           NOT NULL CHECK (numero_cuota > 0),
    fecha_programada  DATE          NOT NULL,
    fecha_pago        DATE,
    monto_programado  NUMERIC(12,2) NOT NULL CHECK (monto_programado > 0),
    monto_pagado      NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (monto_pagado >= 0),
    dias_mora         INT           NOT NULL DEFAULT 0 CHECK (dias_mora >= 0),
    estado_pago       VARCHAR(20)   NOT NULL CHECK (estado_pago IN ('Vigente','Vencido','Pagado')),
    CONSTRAINT uq_prestamo_cuota UNIQUE (prestamo_id, numero_cuota)
);

-- ── 9. TRANSACCIÓN ───────────────────────────────────────────
CREATE TABLE oltp.transaccion (
    transaccion_id   BIGSERIAL     PRIMARY KEY,
    cuenta_id        INT           NOT NULL REFERENCES oltp.cuenta(cuenta_id),
    producto_id      INT           NOT NULL REFERENCES oltp.producto(producto_id),
    canal_id         INT           NOT NULL REFERENCES oltp.canal(canal_id),
    agencia_id       INT           NOT NULL REFERENCES oltp.agencia(agencia_id),
    fecha            TIMESTAMP     NOT NULL,
    monto            NUMERIC(14,2) NOT NULL CHECK (monto > 0),
    tipo_transaccion VARCHAR(30)   NOT NULL CHECK (tipo_transaccion IN ('Depósito','Retiro','Transferencia','Pago de Servicio','Compra'))
);

-- ── 10. SEGURO ───────────────────────────────────────────────
CREATE TABLE oltp.seguro (
    seguro_id      SERIAL        PRIMARY KEY,
    cliente_id     INT           NOT NULL REFERENCES oltp.cliente(cliente_id),
    producto_id    INT           NOT NULL REFERENCES oltp.producto(producto_id),
    tipo_seguro    VARCHAR(30)   NOT NULL CHECK (tipo_seguro IN ('Vida','Vehicular','Hogar','Desgravamen')),
    prima_mensual  NUMERIC(10,2) NOT NULL CHECK (prima_mensual > 0),
    fecha_inicio   DATE          NOT NULL,
    estado         VARCHAR(20)   NOT NULL CHECK (estado IN ('Activo','Cancelado','Vencido'))
);

-- ── ÍNDICES para mejorar rendimiento en consultas analíticas ──
CREATE INDEX idx_transaccion_cuenta   ON oltp.transaccion(cuenta_id);
CREATE INDEX idx_transaccion_fecha    ON oltp.transaccion(fecha);
CREATE INDEX idx_transaccion_canal    ON oltp.transaccion(canal_id);
CREATE INDEX idx_pago_prestamo        ON oltp.pago(prestamo_id);
CREATE INDEX idx_prestamo_cliente     ON oltp.prestamo(cliente_id);
CREATE INDEX idx_cuenta_cliente       ON oltp.cuenta(cliente_id);
CREATE INDEX idx_cuenta_estado        ON oltp.cuenta(estado);

-- ── VERIFICACIÓN ─────────────────────────────────────────────
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'oltp'
ORDER BY table_name;


TRUNCATE oltp.cliente RESTART IDENTITY CASCADE;