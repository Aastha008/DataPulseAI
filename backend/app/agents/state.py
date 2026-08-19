from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    user_query: str
    provider: str = "gemini"
    api_key: Optional[str] = None
    
    # Classification & Planning
    intent: Optional[str] = None  # "AB_TEST", "ROOT_CAUSE", "FUNNEL", "GENERAL"
    reasoning_steps: List[str] = Field(default_factory=list)
    
    # SQL Execution & Self-Healing
    generated_sql: Optional[str] = None
    sql_execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    sql_retries: int = 0
    sql_error: Optional[str] = None
    query_result_data: Optional[List[Dict[str, Any]]] = None
    query_columns: Optional[List[str]] = None
    execution_time_ms: float = 0.0
    
    # Statistical Rigor
    stats_results: Optional[Dict[str, Any]] = None
    srm_results: Optional[Dict[str, Any]] = None
    
    # Synthesis & Output
    executive_memo: Optional[str] = None
    plotly_chart_spec: Optional[Dict[str, Any]] = None
    final_response: Optional[str] = None
