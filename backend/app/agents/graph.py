from .state import AgentState
from .router import route_query
from .sql_agent import generate_and_execute_sql
from .insight_generator import synthesize_analysis

class AnalyticsAgentWorkflow:
    def __init__(self):
        pass
        
    def run(self, state: AgentState) -> AgentState:
        state = route_query(state)
        state = generate_and_execute_sql(state)
        state = synthesize_analysis(state)
        state.final_response = state.executive_memo
        return state

agent_workflow = AnalyticsAgentWorkflow()
