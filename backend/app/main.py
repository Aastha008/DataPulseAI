import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .guardrails.validator import AnalysisRequest
from .agents.state import AgentState
from .agents.graph import agent_workflow
from .database.db import db_manager

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": settings.DATABASE_PATH
    }

@app.get("/api/schema")
def get_schema():
    con = db_manager.get_connection()
    tables_res = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
    tables = [t[0] for t in tables_res]
    
    schema_details = {}
    for tbl in tables:
        cols = con.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{tbl}'").fetchall()
        cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        schema_details[tbl] = {
            "row_count": cnt,
            "columns": [{"name": c[0], "type": c[1]} for c in cols]
        }
    con.close()
    return {"tables": schema_details}

@app.post("/api/query")
def run_analytics_query(req: AnalysisRequest):
    try:
        init_state = AgentState(
            user_query=req.query,
            provider=req.provider or settings.DEFAULT_PROVIDER,
            api_key=req.api_key
        )
        final_state = agent_workflow.run(init_state)
        return final_state.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
