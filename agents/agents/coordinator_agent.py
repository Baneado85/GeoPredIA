class CoordinatorAgent:
    def synthesize(self, geo_report: dict, env_report: dict, soc_report: dict, global_score: float) -> dict:
        critical_alerts = []
        if env_report["severity"] == "Alto":
            critical_alerts.append("ALERTA CRÍTICA: RIESGO AMBIENTAL SEVERO DETECTADO")
        if geo_report["severity"] == "Alto":
            critical_alerts.append("ALERTA CRÍTICA: RIESGO GEOLÓGICO ELEVADO")

        synthesis_markdown = f"""
### 📊 Informe Técnico de Evaluación GeoPredIA

**Riesgo Global Ponderado**: `{global_score} / 100`

#### 1. Análisis Geológico ({geo_report['severity']})
- {geo_report['findings'][0]}
- **Recomendación**: {geo_report['recommendation']}

#### 2. Análisis Ambiental ({env_report['severity']})
- {env_report['findings'][0]}
- **Recomendación**: {env_report['recommendation']}

#### 3. Licencia Social ({soc_report['severity']})
- {soc_report['findings'][0]}
- **Recomendación**: {soc_report['recommendation']}

---
*Evaluación generada automáticamente por el Sistema Multi-Agente GeoPredIA AI para SAP Build Process Automation.*
"""
        return {
            "global_risk_score": global_score,
            "critical_alerts": critical_alerts,
            "synthesis_markdown": synthesis_markdown.strip()
        }
