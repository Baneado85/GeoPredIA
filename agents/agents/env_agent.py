class EnvAgent:
    def analyze(self, env_score: float, zone_data: dict, iot_alerts: list = None) -> dict:
        severity = "Bajo" if env_score < 30 else ("Medio" if env_score < 60 else "Alto")
        findings = []
        if env_score >= 50:
            findings.append("Cuerpos de agua cercanos muestran sensibilidad a la turbidez.")
        if iot_alerts:
            findings.append(f"Se registraron {len(iot_alerts)} alertas de sensores IoT Sentinel en las ultimas 24h.")
            
        return {
            "agent": "Agente Ambiental",
            "score": env_score,
            "severity": severity,
            "findings": findings,
            "recommendation": "Instalar piscinas de decantación previo a cualquier movimiento de tierras."
        }
