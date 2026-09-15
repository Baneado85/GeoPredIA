class GeoAgent:
    def analyze(self, geo_score: float, zone_data: dict) -> dict:
        severity = "Bajo" if geo_score < 30 else ("Medio" if geo_score < 60 else "Alto")
        findings = []
        if geo_score >= 60:
            findings.append("Elevada densidad de fallas estructurales y terreno inestable.")
        else:
            findings.append("Formación litológica estable para exploración inicial.")
            
        return {
            "agent": "Agente Geológico",
            "score": geo_score,
            "severity": severity,
            "findings": findings,
            "recommendation": "Realizar 2 perforaciones adicionales de confirmación en el cuadrante Norte."
        }
