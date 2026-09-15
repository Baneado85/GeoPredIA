# Especificación GeoPredIA para SAP Analytics Cloud

Estado: diseño para configurar en el tenant del hackathon. Este Markdown no es un paquete de modelo SAC importable. El repositorio funciona con datos sintéticos para desarrollar la experiencia; la evaluación oficial debe ejecutarse en SAC sobre el dataset común alojado en HANA Cloud.

## 1. Contrato antes del dashboard

Inventariar las columnas reales, su unidad, rango, dirección de riesgo, granularidad, fecha y faltantes. Guardar el mapeo completado a partir de `sac_indicator_mapping.template.csv`. No asumir que una tabla contiene fallas geológicas, comunidades o calidad de agua porque lo sugiera el nombre del reto. Una coordenada faltante impide ubicar una zona con precisión; no inventar una ubicación.

Definir una fila analítica por zona y versión de datos. Al combinar tablas, verificar cardinalidad: varias observaciones por zona no deben multiplicar sus scores. Las mediciones IoT forman una serie temporal adicional con fuente y calibración propias.

## 2. Cálculos dentro de SAC

Implementar medidas calculadas en el modelo o en la historia según el tipo de conexión y las capacidades habilitadas. Las expresiones siguientes son notación matemática, **no código para pegar sin adaptación** en el editor SAC.

Para un indicador con más riesgo cuando aumenta:

`normalizado = 100 × limitar((valor − L) / (U − L), 0, 1)`

Para uno con más riesgo cuando disminuye:

`normalizado = 100 × (1 − limitar((valor − L) / (U − L), 0, 1))`

`L` y `U` son referencias técnicas acordadas y versionadas, no extremos recalculados al filtrar el dashboard. Si `U <= L`, hay valores faltantes o una categoría no mapeada, el indicador queda sin evaluar. Las categorías requieren una tabla de reglas explícita validada por el equipo. Registrar la razón para cada regla.

Por dimensión, usar una media ponderada de sus indicadores requeridos; los pesos deben sumar 1. En el MVP, si falta un indicador requerido, el subíndice queda sin evaluar. No renormalizar silenciosamente los pesos para ocultar faltantes.

**Ejemplo educativo de pesos globales, pendiente de justificación:**

`global_risk = 0.40 × geological + 0.35 × environmental + 0.25 × social`

Si falta cualquier subíndice, `global_risk` queda vacío/null y el caso necesita datos. El promedio no permite compensar una condición crítica: mostrar dicha condición por separado y enviarla a revisión humana. No existe todavía una lista oficial validada de umbrales críticos en este repositorio.

Estos pesos no han sido entrenados ni validados. El riesgo relativo no mide rentabilidad, reservas ni probabilidad de desastre. Los agentes usan los resultados congelados de SAC como evidencia, sin reemplazar el cálculo.

## 3. Historia ejecutiva mínima

| Sección | Contenido |
|---|---|
| Resumen | Zonas evaluables / total; riesgo promedio solo de evaluables; zonas pendientes de revisión; cobertura de datos |
| Ranking | Zonas de menor a mayor riesgo, con versión y tres subíndices; los casos incompletos se listan aparte |
| Comparación | Dos o más zonas, indicadores y principales diferencias verificables |
| Explicación | Indicadores, normalización, pesos, faltantes y condiciones de revisión |
| Escenarios | Pesos alternativos cuya suma sea 1, con cambio de ranking y versión del escenario |
| Sentinel | Lecturas y fecha, dispositivo, zona, origen real/simulado y estado de calibración |

Evitar sumar scores entre zonas: representan índices, no cantidades aditivas. Comprobar los totales/agrupaciones en el modelo y la historia. El mapa solo se habilita cuando existen coordenadas válidas y permiso para usarlas.

## 4. Exportación reproducible

Crear una tabla a nivel de zona con los tres subíndices y score global calculados. Exportarla desde el menú de la tabla, seleccionando el alcance **Point of view** cuando se necesiten los resultados calculados visibles. Verificar este comportamiento con la tabla y versión del tenant: el CSV exportado puede incluir encabezados, unidades, escala o formatos regionales que requieren adaptación.

Adaptar una copia al contrato plano descrito en `sac_snapshot_contract.md`; conservar el archivo original. Escribir la fecha de evaluación y las versiones de modelo/dataset de la ejecución, no la hora inventada de un sensor. Cualquier extracción sigue siendo manual hasta implementar y probar una integración soportada por el tenant.

## 5. Criterios de aceptación

1. Recalcular a mano al menos tres zonas y comparar con SAC, incluida una con faltantes.
2. Filtrar una región y comprobar que las referencias `L/U` no cambian.
3. Mostrar una condición de revisión que no desaparezca por promediar.
4. Exportar un resultado con decimales y verificar que el importador lo conserva.
5. Cambiar pesos en un escenario sin sobrescribir una evaluación ya revisada.
6. Separar todas las lecturas `source=simulator` en la presentación.

Fuente SAP: [Exportar datos de una tabla](https://help.sap.com/doc/00f68c2e08b941f081002fd3691d86a7/2023.20/en-US/ff5f1e052b5e400da990dad8408604da.html). Consultar también la ayuda de la versión disponible en el tenant.
