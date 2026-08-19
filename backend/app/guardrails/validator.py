import re
from typing import Tuple, List, Optional
from pydantic import BaseModel, Field

class AnalysisRequest(BaseModel):
    query: str = Field(..., description="User question or analysis request")
    provider: Optional[str] = Field("gemini", description="LLM provider: gemini, openai, groq, mock")
    api_key: Optional[str] = Field(None, description="Optional API key override")
    confidence_level: Optional[float] = Field(0.95, description="Statistical confidence level (default 0.95)")

class SQLGuardrail:
    FORBIDDEN_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
        "ATTACH", "DETACH", "CREATE", "REPLACE", "EXEC", "EXECUTE",
        "COPY", "EXPORT", "INSTALL", "LOAD"
    ]
    
    ALLOWED_TABLES = ["users", "sessions", "events", "experiments"]

    @classmethod
    def validate_sql(cls, sql: str) -> Tuple[bool, Optional[str]]:
        clean_sql = re.sub(r"--.*?$|/\*.*?\*/", "", sql, flags=re.MULTILINE).strip()
        
        if not clean_sql:
            return False, "Empty SQL query."
            
        upper_sql = clean_sql.upper()
        
        # Check forbidden destructive statements
        for kw in cls.FORBIDDEN_KEYWORDS:
            pattern = rf"\b{kw}\b"
            if re.search(pattern, upper_sql):
                return False, f"SQL contains forbidden mutation keyword: {kw}. Only read-only SELECT queries are permitted."
                
        # Must start with SELECT or WITH
        if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
            return False, "Query must start with SELECT or WITH clause."
            
        return True, None
