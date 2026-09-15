from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from agents.geo_agent import GeoAgent
from agents.env_agent import EnvAgent
from agents.social_agent import SocialAgent
from agents.coordinator_agent import CoordinatorAgent

app = FastAPI(title="GeoPredIA Multi-Agent AI API")

geo_agent = GeoAgent()
env_agent = EnvAgent()
soc_agent = SocialAgent()
coord_agent = CoordinatorAgent()

class EvaluationRequest(BaseModel):
    zone_id: str
    geo_score: float
    env_score: float
    soc_score: float
    global_score: float
    iot_alerts: Optional[List[str]] = []

@app.get("/")
def read_root():
    return {"status": "ACTIVE", "system": "GeoPredIA Multi-Agent Orchestrator"}

@app.post("/api/v1/analyze")
def analyze_evaluation(req: EvaluationRequest):
    geo_res = geo_agent.analyze(req.geo_score, {"zone_id": req.zone_id})
    env_res = env_agent.analyze(req.env_score, {"zone_id": req.zone_id}, req.iot_alerts)
    soc_res = soc_agent.analyze(req.soc_score, {"zone_id": req.zone_id})
    
    final_synthesis = coord_agent.synthesize(geo_res, env_res, soc_res, req.global_score)
    return {
        "status": "SUCCESS",
        "zone_id": req.zone_id,
        "details": {
            "geo": geo_res,
            "env": env_res,
            "social": soc_res
        },
        "synthesis": final_synthesis
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
