-- ============================================================
-- Customer 360 Bancario
-- Fase 3 — Datos base: Canal y Agencia
-- ============================================================

-- ── CANALES ──────────────────────────────────────────────────
INSERT INTO oltp.canal (nombre) VALUES
    ('ATM'),
    ('App'),
    ('Web'),
    ('Agencia'),
    ('Call Center');

-- ── AGENCIAS FÍSICAS ─────────────────────────────────────────
INSERT INTO oltp.agencia (nombre, ciudad, distrito, es_virtual) VALUES
    ('Agencia Central',        'Lima',         'Cercado de Lima',  FALSE),
    ('Agencia Miraflores',     'Lima',         'Miraflores',       FALSE),
    ('Agencia San Isidro',     'Lima',         'San Isidro',       FALSE),
    ('Agencia Surco',          'Lima',         'Santiago de Surco', FALSE),
    ('Agencia San Borja',      'Lima',         'San Borja',        FALSE),
    ('Agencia Callao',         'Callao',       'Callao',           FALSE),
    ('Agencia Arequipa Centro','Arequipa',     'Cercado',          FALSE),
    ('Agencia Cayma',          'Arequipa',     'Cayma',            FALSE),
    ('Agencia Trujillo Centro','Trujillo',     'Trujillo',         FALSE),
    ('Agencia El Porvenir',    'Trujillo',     'El Porvenir',      FALSE),
    ('Agencia Chiclayo',       'Chiclayo',     'Chiclayo',         FALSE),
    ('Agencia Piura Centro',   'Piura',        'Piura',            FALSE),
    ('Agencia Cusco',          'Cusco',        'Cusco',            FALSE),
    ('Agencia Iquitos',        'Iquitos',      'Iquitos',          FALSE),
    ('Agencia Huancayo',       'Huancayo',     'Huancayo',         FALSE);

-- ── AGENCIA VIRTUAL (canal digital) ──────────────────────────
-- Registro especial requerido por regla de negocio 18:
-- agencia_id obligatorio en Transaccion; canales App, Web y ATM
-- sin sede física apuntan a este registro.
INSERT INTO oltp.agencia (nombre, ciudad, distrito, es_virtual) VALUES
    ('Canal Digital', NULL, NULL, TRUE);

-- ── PRODUCTOS ────────────────────────────────────────────────
INSERT INTO oltp.producto (nombre, categoria, comision_pct, costo_fondeo_pct) VALUES
    -- Cuentas
    ('Cuenta de Ahorros Estándar',  'Cuenta',    0.0010, 0.0200),
    ('Cuenta Corriente Empresarial','Cuenta',    0.0015, 0.0180),
    ('Cuenta Plazo Fijo 180 días',  'Cuenta',    0.0005, 0.0350),
    -- Tarjetas
    ('Tarjeta Débito Clásica',      'Tarjeta',   0.0008, 0.0000),
    ('Tarjeta Crédito Oro',         'Tarjeta',   0.0200, 0.0450),
    ('Tarjeta Crédito Platinum',    'Tarjeta',   0.0250, 0.0420),
    -- Préstamos
    ('Préstamo Personal Estándar',  'Préstamo',  0.0000, 0.0600),
    ('Préstamo Vehicular',          'Préstamo',  0.0000, 0.0550),
    ('Préstamo Hipotecario Simple', 'Préstamo',  0.0000, 0.0480),
    -- Seguros
    ('Seguro de Vida Básico',       'Seguro',    0.0500, 0.0000),
    ('Seguro Vehicular Estándar',   'Seguro',    0.0450, 0.0000),
    ('Seguro de Hogar',             'Seguro',    0.0400, 0.0000),
    ('Seguro Desgravamen',          'Seguro',    0.0300, 0.0000);

-- ── VERIFICACIÓN ─────────────────────────────────────────────
SELECT 'canal'    AS tabla, COUNT(*) AS registros FROM oltp.canal
UNION ALL
SELECT 'agencia',           COUNT(*)               FROM oltp.agencia
UNION ALL
SELECT 'producto',          COUNT(*)               FROM oltp.producto;