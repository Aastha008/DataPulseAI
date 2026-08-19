from typing import Dict, Any
from .state import AgentState

def route_query(state: AgentState) -> AgentState:
    q = state.user_query.lower()
    if any(k in q for k in ['a/b test', 'ab test', 'experiment', 'variant', 'treatment', 'control', 'srm', 'sample ratio mismatch', 'lift', 'p-value', 'statistical significance']):
        state.intent = 'AB_TEST'
        state.reasoning_steps.append('Intent Classified: A/B Testing & Experimentation Evaluation (Will run hypothesis testing & SRM checks)')
    elif any(k in q for k in ['funnel', 'drop-off', 'drop off', 'stage', 'checkout flow', 'cart to checkout', 'step by step']):
        state.intent = 'FUNNEL'
        state.reasoning_steps.append('Intent Classified: Conversion Funnel Stage-by-Stage Drop-off Analysis')
    elif any(k in q for k in ['why did', 'drop', 'dropped', 'fell', 'spike', 'spiked', 'anomaly', 'root cause', 'decrease', 'increase', 'driver']):
        state.intent = 'ROOT_CAUSE'
        state.reasoning_steps.append('Intent Classified: Root-Cause & Dimensional Anomaly Investigation')
    else:
        state.intent = 'GENERAL'
        state.reasoning_steps.append('Intent Classified: General Product & Business Metric Analytics')
    return state
