# Contrato de snapshot de evaluación

Un snapshot es una copia congelada de los resultados de una evaluación: identifica exactamente lo que vio el revisor. No actualizar sus scores después de iniciar una revisión. Una reevaluación genera un nuevo ID.

## Archivo de intercambio

UTF-8, encabezado único, coma como separador, punto decimal, sin separadores de miles, unidades ni `%`. Usar ID de zona real, no el nombre visible. Cada fila contiene:

```csv
zone_id,evaluated_at,model_version,dataset_version,geological,environmental,social,global_risk
```

| Campo | Validación |
|---|---|
| `zone_id` | ID presente en el catálogo de zonas de la ejecución |
| `evaluated_at` | ISO 8601 con zona horaria, preferentemente UTC terminado en `Z` |
| `model_version` | Versión de reglas, normalización y pesos, obligatoria |
| `dataset_version` | Identificador reproducible del conjunto de datos, obligatorio |
| Tres subíndices | Número entre 0 y 100, o celda vacía para null |
| `global_risk` | Número entre 0 y 100; vacío si falta cualquiera de los subíndices |

Una celda vacía significa «sin evaluar»; `0` es un resultado numérico y nunca representa un error. Rechazar NaN, Infinity, porcentajes y valores fuera de rango. No completar resultados oficiales con valores sintéticos. Los errores deben mostrar la fila/columna que requiere corrección.

El archivo `sac_demo_snapshot.csv` contiene **ejemplos inventados**, no fue exportado de un tenant SAC. Sirve para discutir el contrato y probar validaciones. Sus versiones empiezan por `demo`/`synthetic` para conservar esa procedencia.

## Adaptación de un export real

1. Conservar el export SAC original y anotar historia/modelo, filtros, escenario y hora.
2. Quitar filas de título y totales; mantener una fila por zona evaluada.
3. Renombrar encabezados a los del contrato. Si la configuración regional usa coma decimal, convertirla explícitamente antes de emitir un CSV separado por comas.
4. Añadir las versiones documentadas y la fecha de la evaluación. No recalcular los scores en Excel, Python o el backend para presentarlos como resultados SAC.
5. Comparar tres filas contra la tabla de SAC, incluidos nulos y decimales.
6. Importar con un usuario autorizado; conservar hash del archivo y procedencia en una implementación de producción.

El backend transforma los campos planos a `subindices: {geological, environmental, social}` y `global_risk`. Genera `evaluation_id` y registra la procedencia. El formulario BPA referencia ese ID y lleva una copia de valores/versión. El endpoint de telemetría no crea ni modifica snapshots.

Si el importador de la versión de la aplicación no conserva todos los metadatos de auditoría propuestos aquí, registrarlos junto al export original y completar esa integración antes de una entrega productiva.
