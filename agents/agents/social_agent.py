class SocialAgent:
    def analyze(self, soc_score: float, zone_data: dict) -> dict:
        severity = "Bajo" if soc_score < 30 else ("Medio" if soc_score < 60 else "Alto")
        findings = []
        if soc_score < 40:
            findings.append("Comunidades locales cuentan con convenios de desarrollo sostenible firmados.")
        else:
            findings.append("Existen solicitudes de consulta previa pendientes de resolución.")
            
        return {
            "agent": "Agente Social",
            "score": soc_score,
            "severity": severity,
            "findings": findings,
            "recommendation": "Mantener mesas de dialogo quincenales y publicar reportes de monitoreo participativo."
        }
