-- ============================================================
-- Customer 360 Bancario
-- Fase 4 — Consultas SQL analíticas
-- ============================================================

-- QUERY 1: Top 10 clientes más rentables
SELECT 
	c.nombre_completo,
	c.ciudad,
	ROUND(SUM(t.ingreso_comision), 2) AS ingreso_transacciones,
	ROUND(SUM(p.margen_estimado), 2) AS margen_prestamos,
	ROUND(SUM(t.ingreso_comision) + 
			COALESCE(SUM(p.margen_estimado), 0), 2) AS rentabilidad_total
FROM dw.dim_cliente c
JOIN dw.fact_transacciones t  ON t.cliente_sk = c.cliente_sk
LEFT JOIN dw.fact_prestamos p ON p.cliente_sk = c.cliente_sk
GROUP BY c.cliente_sk, c.nombre_completo, c.ciudad
ORDER BY rentabilidad_total DESC
LIMIT 10;

-- QUERY 2: Índice de morosidad por ciudad
SELECT 
    c.ciudad,
    COUNT(p.prestamo_id) AS total_prestamos,
    SUM(CASE WHEN p.es_default THEN 1 ELSE 0 END) AS prestamos_default,
    ROUND(SUM(CASE WHEN p.es_default THEN 1 ELSE 0 END) * 100.0 /
          COUNT(p.prestamo_id), 2) AS indice_morosidad_pct,
    ROUND(SUM(CASE WHEN p.es_default THEN p.monto ELSE 0 END), 2) AS monto_en_riesgo	
FROM dw.fact_prestamos p
JOIN dw.dim_cliente c ON c.cliente_sk = p.cliente_sk
GROUP BY c.ciudad
ORDER BY indice_morosidad_pct DESC;


-- QUERY 3: Canal más utilizado y más rentable
SELECT
    ca.nombre                            AS canal,
    COUNT(t.transaccion_id)              AS total_transacciones,
    ROUND(SUM(t.monto), 2)               AS monto_total,
    ROUND(AVG(t.monto), 2)               AS ticket_promedio,
    ROUND(SUM(t.ingreso_comision), 2)    AS ingreso_comision_total
FROM dw.fact_transacciones t
JOIN dw.dim_canal ca ON ca.canal_sk = t.canal_sk
GROUP BY ca.nombre
ORDER BY total_transacciones DESC;


-- QUERY 4: Clientes en riesgo de abandono (churn)
SELECT
    c.nombre_completo,
    c.ciudad,
    c.antiguedad_meses,
    MAX(cu.fecha_ultimo_movimiento)      AS ultimo_movimiento,
    CURRENT_DATE - MAX(cu.fecha_ultimo_movimiento) AS dias_sin_transaccion,
    COUNT(cu.cuenta_id)                  AS total_cuentas
FROM dw.dim_cliente c
JOIN oltp.cuenta cu ON cu.cliente_id = c.cliente_id
WHERE cu.estado = 'Inactiva'
GROUP BY c.cliente_sk, c.nombre_completo, c.ciudad, c.antiguedad_meses
HAVING MAX(CURRENT_DATE - cu.fecha_ultimo_movimiento) > 90
ORDER BY dias_sin_transaccion DESC
LIMIT 15;

-- QUERY 5: Productos más rentables
SELECT
    pr.nombre                            AS producto,
    pr.categoria,
    COUNT(t.transaccion_id)              AS total_transacciones,
    ROUND(SUM(t.monto), 2)               AS monto_total,
    ROUND(SUM(t.ingreso_comision), 2)    AS ingreso_comision_total,
    ROUND(AVG(t.monto), 2)               AS ticket_promedio
FROM dw.fact_transacciones t
JOIN dw.dim_producto pr ON pr.producto_sk = t.producto_sk
GROUP BY pr.producto_sk, pr.nombre, pr.categoria
ORDER BY ingreso_comision_total DESC;


-- QUERY 6: Monto en Riesgo Latente 
SELECT
    c.ciudad,
    COUNT(p.prestamo_id)                 AS creditos_vigentes,
    ROUND(SUM(p.monto), 2)               AS monto_total_vigente,
    ROUND(SUM(CASE WHEN p.max_dias_mora BETWEEN 30 AND 90
                   THEN p.monto ELSE 0 END), 2) AS monto_riesgo_latente,
    ROUND(SUM(CASE WHEN p.max_dias_mora BETWEEN 30 AND 90
                   THEN p.monto ELSE 0 END) * 100.0 /
          SUM(p.monto), 2)               AS pct_riesgo_latente
FROM dw.fact_prestamos p
JOIN dw.dim_cliente c ON c.cliente_sk = p.cliente_sk
WHERE p.es_default = FALSE
GROUP BY c.ciudad
ORDER BY monto_riesgo_latente DESC;

-- QUERY 7: Productos por segmento de clientes (cross-selling)
SELECT
    c.ciudad,
    COUNT(DISTINCT c.cliente_sk)             AS total_clientes,
    ROUND(AVG(c.ingreso_mensual), 2)         AS ingreso_promedio,
    COUNT(DISTINCT fp.prestamo_id)           AS total_prestamos,
    COUNT(DISTINCT fpc.contrato_id)          AS total_productos_contratados,
    ROUND(COUNT(DISTINCT fpc.contrato_id) * 1.0 /
          COUNT(DISTINCT c.cliente_sk), 2)   AS productos_por_cliente
FROM dw.dim_cliente c
LEFT JOIN dw.fact_prestamos fp  ON fp.cliente_sk = c.cliente_sk
LEFT JOIN dw.fact_productos_contratados fpc ON fpc.cliente_sk = c.cliente_sk
GROUP BY c.ciudad
ORDER BY productos_por_cliente DESC;