-- ============================================================
-- Customer 360 Bancario
-- Fase 3 — Modelo B: Esquema Estrella (Data Warehouse)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS dw;

-- ── DIMENSIONES ───────────────────────────────────────────────

-- DIM_FECHA
CREATE TABLE dw.dim_fecha (
    fecha_sk    SERIAL      PRIMARY KEY,
    fecha       DATE        NOT NULL UNIQUE,
    anio        INT         NOT NULL,
    mes         INT         NOT NULL CHECK (mes BETWEEN 1 AND 12),
    trimestre   INT         NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    dia_semana  VARCHAR(20) NOT NULL,
    es_fin_semana BOOLEAN   NOT NULL
);

-- DIM_CLIENTE
CREATE TABLE dw.dim_cliente (
    cliente_sk       SERIAL         PRIMARY KEY,
    cliente_id       INT            NOT NULL UNIQUE,
    nombre_completo  VARCHAR(160)   NOT NULL,
    edad             INT            NOT NULL,
    sexo             CHAR(1)        NOT NULL,
    estado_civil     VARCHAR(20)    NOT NULL,
    profesion        VARCHAR(80),
    ingreso_mensual  NUMERIC(12,2)  NOT NULL,
    ciudad           VARCHAR(60),
    segmento_rfm     VARCHAR(30),   -- NULL hasta Fase 6
    antiguedad_meses INT            NOT NULL,
    fecha_registro   DATE           NOT NULL,
    fecha_carga      TIMESTAMP      NOT NULL DEFAULT NOW()
);

-- DIM_PRODUCTO
CREATE TABLE dw.dim_producto (
    producto_sk      SERIAL        PRIMARY KEY,
    producto_id      INT           NOT NULL UNIQUE,
    nombre           VARCHAR(80)   NOT NULL,
    categoria        VARCHAR(30)   NOT NULL,
    comision_pct     NUMERIC(5,4)  NOT NULL,
    costo_fondeo_pct NUMERIC(5,4)  NOT NULL
);

-- DIM_CANAL
CREATE TABLE dw.dim_canal (
    canal_sk  SERIAL      PRIMARY KEY,
    canal_id  INT         NOT NULL UNIQUE,
    nombre    VARCHAR(30) NOT NULL
);

-- DIM_AGENCIA
CREATE TABLE dw.dim_agencia (
    agencia_sk  SERIAL      PRIMARY KEY,
    agencia_id  INT         NOT NULL UNIQUE,
    nombre      VARCHAR(60) NOT NULL,
    ciudad      VARCHAR(60),
    distrito    VARCHAR(60),
    es_virtual  BOOLEAN     NOT NULL
);

-- ── TABLAS DE HECHOS ──────────────────────────────────────────

-- FACT_TRANSACCIONES
CREATE TABLE dw.fact_transacciones (
    transaccion_id    BIGINT        PRIMARY KEY,
    cliente_sk        INT           NOT NULL REFERENCES dw.dim_cliente(cliente_sk),
    fecha_sk          INT           NOT NULL REFERENCES dw.dim_fecha(fecha_sk),
    producto_sk       INT           NOT NULL REFERENCES dw.dim_producto(producto_sk),
    canal_sk          INT           NOT NULL REFERENCES dw.dim_canal(canal_sk),
    agencia_sk        INT           NOT NULL REFERENCES dw.dim_agencia(agencia_sk),
    tipo_transaccion  VARCHAR(30)   NOT NULL,
    monto             NUMERIC(14,2) NOT NULL,
    ingreso_comision  NUMERIC(12,2) NOT NULL DEFAULT 0
);

-- FACT_PRESTAMOS
CREATE TABLE dw.fact_prestamos (
    prestamo_id          INT           PRIMARY KEY,
    cliente_sk           INT           NOT NULL REFERENCES dw.dim_cliente(cliente_sk),
    fecha_sk             INT           NOT NULL REFERENCES dw.dim_fecha(fecha_sk),
    producto_sk          INT           NOT NULL REFERENCES dw.dim_producto(producto_sk),
    monto                NUMERIC(14,2) NOT NULL,
    tasa_interes         NUMERIC(6,4)  NOT NULL,
    plazo_meses          INT           NOT NULL,
    ingreso_estimado     NUMERIC(14,2) NOT NULL,
    costo_fondeo_estimado NUMERIC(14,2) NOT NULL,
    score_riesgo         NUMERIC(5,2),           -- NULL hasta Fase 6
    max_dias_mora        INT           NOT NULL DEFAULT 0,
    es_default           BOOLEAN       NOT NULL DEFAULT FALSE,
    margen_estimado      NUMERIC(14,2) NOT NULL
);

-- FACT_PAGOS
CREATE TABLE dw.fact_pagos (
    pago_id      INT         PRIMARY KEY,
    prestamo_id  INT         NOT NULL REFERENCES dw.fact_prestamos(prestamo_id),
    fecha_sk     INT         NOT NULL REFERENCES dw.dim_fecha(fecha_sk),
    dias_mora    INT         NOT NULL DEFAULT 0,
    estado_pago  VARCHAR(20) NOT NULL
);

-- FACT_PRODUCTOS_CONTRATADOS
CREATE TABLE dw.fact_productos_contratados (
    contrato_id      BIGSERIAL     PRIMARY KEY,
    cliente_sk       INT           NOT NULL REFERENCES dw.dim_cliente(cliente_sk),
    fecha_sk         INT           NOT NULL REFERENCES dw.dim_fecha(fecha_sk),
    producto_sk      INT           NOT NULL REFERENCES dw.dim_producto(producto_sk),
    tipo_producto    VARCHAR(20)   NOT NULL CHECK (tipo_producto IN ('Tarjeta','Seguro')),
    monto_referencia NUMERIC(12,2) NOT NULL,
    estado           VARCHAR(20)   NOT NULL
);

-- ── ÍNDICES ───────────────────────────────────────────────────
CREATE INDEX idx_ft_cliente   ON dw.fact_transacciones(cliente_sk);
CREATE INDEX idx_ft_fecha     ON dw.fact_transacciones(fecha_sk);
CREATE INDEX idx_ft_canal     ON dw.fact_transacciones(canal_sk);
CREATE INDEX idx_fp_cliente   ON dw.fact_prestamos(cliente_sk);
CREATE INDEX idx_fp_default   ON dw.fact_prestamos(es_default);
CREATE INDEX idx_fp_score     ON dw.fact_prestamos(score_riesgo);
CREATE INDEX idx_fpc_cliente  ON dw.fact_productos_contratados(cliente_sk);

-- ── VERIFICACIÓN ─────────────────────────────────────────────
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'dw'
ORDER BY table_name;