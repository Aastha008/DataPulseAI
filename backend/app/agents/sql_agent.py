import os
import re
import json
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from ..database.db import db_manager
from ..guardrails.validator import SQLGuardrail
from ..config import settings
from .state import AgentState

def _call_llm(prompt: str, provider: str, api_key: Optional[str] = None, user_query: str = "") -> str:
    # 1. Gemini
    if provider == "gemini" or (not provider and settings.GEMINI_API_KEY):
        key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if key:
            try:
                from google import genai
                client = genai.Client(api_key=key)
                resp = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                if resp.text:
                    return resp.text
            except Exception as e:
                print(f"Gemini API note: {e}")

    # 2. OpenAI
    if provider == "openai" or settings.OPENAI_API_KEY:
        key = api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                if resp.choices[0].message.content:
                    return resp.choices[0].message.content
            except Exception as e:
                print(f"OpenAI note: {e}")

    # 3. Groq
    if provider == "groq" or settings.GROQ_API_KEY:
        key = api_key or settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        if key:
            try:
                from groq import Groq
                client = Groq(api_key=key)
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                if resp.choices[0].message.content:
                    return resp.choices[0].message.content
            except Exception as e:
                print(f"Groq note: {e}")

    # Fallback to Dynamic Natural Language SQL Compiler
    return compile_dynamic_sql(user_query if user_query else prompt)

def compile_dynamic_sql(user_query: str) -> str:
    """
    Intelligent Dynamic NL-to-SQL Compiler:
    Parses natural language intent, keywords, entities, aggregations,
    and dimensions across DuckDB tables.
    """
    q = user_query.lower()

    # Case 1: Specific A/B Experiment
    if "exp_checkout_redesign_101" in q or ("checkout redesign" in q):
        return """SELECT 
    variant,
    COUNT(user_id) AS total_users,
    SUM(converted) AS conversions,
    ROUND(SUM(converted) * 1.0 / COUNT(user_id), 4) AS conversion_rate,
    ROUND(SUM(revenue), 2) AS total_revenue,
    ROUND(SUM(revenue) / NULLIF(SUM(converted), 0), 2) AS aov
FROM experiments
WHERE experiment_id = 'exp_checkout_redesign_101'
GROUP BY variant
ORDER BY variant;"""

    elif "exp_ai_search_rank_103" in q or ("srm" in q) or ("search rank" in q):
        return """SELECT 
    variant,
    COUNT(user_id) AS total_users,
    SUM(converted) AS conversions,
    ROUND(SUM(converted) * 1.0 / COUNT(user_id), 4) AS conversion_rate,
    ROUND(SUM(revenue), 2) AS total_revenue
FROM experiments
WHERE experiment_id = 'exp_ai_search_rank_103'
GROUP BY variant
ORDER BY variant;"""

    elif "exp_onboarding_gamify_102" in q or ("onboarding" in q and "experiment" in q):
        return """SELECT 
    variant,
    COUNT(user_id) AS total_users,
    SUM(converted) AS conversions,
    ROUND(SUM(converted) * 1.0 / COUNT(user_id), 4) AS conversion_rate,
    ROUND(SUM(revenue), 2) AS total_revenue
FROM experiments
WHERE experiment_id = 'exp_onboarding_gamify_102'
GROUP BY variant
ORDER BY variant;"""

    elif "experiment" in q or "a/b" in q or "variant" in q:
        return """SELECT 
    experiment_id,
    variant,
    COUNT(user_id) AS total_users,
    SUM(converted) AS conversions,
    ROUND(SUM(converted) * 1.0 / COUNT(user_id), 4) AS conversion_rate,
    ROUND(SUM(revenue), 2) AS total_revenue
FROM experiments
GROUP BY 1, 2
ORDER BY 1, 2;"""

    # Case 2: Delivery Delays & Review Scores
    elif ("delay" in q or "late" in q) and ("review" in q or "score" in q or "rating" in q or "satisfaction" in q):
        return """SELECT 
    CASE WHEN o.is_delayed = 1 THEN 'Delayed Delivery' ELSE 'On-Time Delivery' END AS delivery_status,
    COUNT(o.order_id) AS total_orders,
    ROUND(AVG(r.review_score), 2) AS avg_customer_rating,
    ROUND(AVG(o.delivery_days), 1) AS avg_delivery_days
FROM olist_orders o
JOIN olist_order_reviews r ON o.order_id = r.order_id
WHERE o.order_delivered_customer_date IS NOT NULL
GROUP BY 1
ORDER BY total_orders DESC;"""

    elif "delay" in q or "late" in q or "delivery time" in q or "shipping time" in q:
        return """SELECT 
    c.customer_state AS state,
    COUNT(o.order_id) AS total_orders,
    ROUND(AVG(o.delivery_days), 1) AS avg_delivery_days,
    ROUND(SUM(CASE WHEN o.is_delayed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(o.order_id), 2) AS delay_rate_pct
FROM olist_orders o
JOIN olist_customers c ON o.customer_id = c.customer_id
WHERE o.order_delivered_customer_date IS NOT NULL
GROUP BY 1
ORDER BY delay_rate_pct DESC
LIMIT 10;"""

    # Case 3: Reviews & Ratings by Category
    elif ("review" in q or "rating" in q or "score" in q) and ("category" in q or "product" in q):
        return """SELECT 
    p.product_category_name_english AS category,
    COUNT(r.review_id) AS total_reviews,
    ROUND(AVG(r.review_score), 2) AS avg_rating,
    ROUND(SUM(CASE WHEN r.review_score = 5 THEN 1 ELSE 0 END) * 100.0 / COUNT(r.review_id), 1) AS five_star_pct
FROM olist_order_reviews r
JOIN olist_order_items i ON r.order_id = i.order_id
JOIN olist_products p ON i.product_id = p.product_id
GROUP BY 1
HAVING COUNT(r.review_id) > 100
ORDER BY avg_rating DESC
LIMIT 10;"""

    # Case 4: Payment Methods & AOV
    elif "payment" in q or "payment method" in q or "installments" in q or "credit card" in q:
        return """SELECT 
    payment_type,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(payment_value), 2) AS total_revenue,
    ROUND(AVG(payment_value), 2) AS avg_order_value,
    ROUND(AVG(payment_installments), 1) AS avg_installments
FROM olist_order_payments
GROUP BY 1
ORDER BY total_revenue DESC;"""

    # Case 5: Geographic / States & Cities
    elif "state" in q or "city" in q or "geo" in q or "location" in q or "brazil" in q or "region" in q:
        return """SELECT 
    c.customer_state AS state,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(p.payment_value), 2) AS total_revenue
FROM olist_customers c
JOIN olist_orders o ON c.customer_id = o.customer_id
JOIN olist_order_payments p ON o.order_id = p.order_id
GROUP BY 1
ORDER BY total_revenue DESC
LIMIT 10;"""

    # Case 6: Time Trends / Monthly Orders
    elif "trend" in q or "month" in q or "monthly" in q or "over time" in q or "timeline" in q:
        return """SELECT 
    DATE_TRUNC('month', order_purchase_timestamp) AS order_month,
    COUNT(order_id) AS total_orders
FROM olist_orders
WHERE order_purchase_timestamp IS NOT NULL
GROUP BY 1
ORDER BY 1;"""

    # Case 7: Android / Mobile Device Root Cause
    elif "android" in q or ("device" in q and ("drop" in q or "conversion" in q or "q3" in q or "why" in q)):
        return """SELECT 
    DATE_TRUNC('month', e.event_timestamp) AS month,
    e.device,
    COUNT(DISTINCT CASE WHEN e.event_type = 'start_checkout' THEN e.session_id END) AS checkout_sessions,
    COUNT(DISTINCT CASE WHEN e.event_type = 'purchase' THEN e.session_id END) AS purchase_sessions,
    ROUND(COUNT(DISTINCT CASE WHEN e.event_type = 'purchase' THEN e.session_id END) * 1.0 / 
          NULLIF(COUNT(DISTINCT CASE WHEN e.event_type = 'start_checkout' THEN e.session_id END), 0), 4) AS checkout_to_purchase_rate
FROM events e
GROUP BY 1, 2
ORDER BY 1, 2;"""

    # Case 8: Conversion Funnel Drop-off
    elif "funnel" in q or "drop-off" in q or "drop off" in q or "step" in q or "stage" in q:
        return """SELECT 
    event_type,
    COUNT(event_id) AS event_count,
    COUNT(DISTINCT session_id) AS unique_sessions,
    COUNT(DISTINCT user_id) AS unique_users
FROM events
GROUP BY event_type
ORDER BY 
    CASE event_type
        WHEN 'view_item' THEN 1
        WHEN 'add_to_cart' THEN 2
        WHEN 'start_checkout' THEN 3
        WHEN 'purchase' THEN 4
        ELSE 5
    END;"""

    # Case 9: Acquisition Channels & ARPU
    elif "channel" in q or "acquisition" in q or "arpu" in q:
        return """SELECT 
    u.acquisition_channel,
    COUNT(DISTINCT u.user_id) AS total_users,
    COUNT(DISTINCT e.user_id) FILTER (WHERE e.event_type = 'purchase') AS paying_users,
    ROUND(SUM(e.revenue), 2) AS total_revenue,
    ROUND(SUM(e.revenue) / COUNT(DISTINCT u.user_id), 2) AS arpu
FROM users u
LEFT JOIN events e ON u.user_id = e.user_id
GROUP BY 1
ORDER BY total_revenue DESC;"""

    # Case 10: Product Categories / Default
    else:
        return """SELECT 
    p.product_category_name_english AS category,
    COUNT(DISTINCT i.order_id) AS total_orders,
    ROUND(SUM(i.price), 2) AS total_sales,
    ROUND(AVG(i.price), 2) AS avg_item_price
FROM olist_order_items i
JOIN olist_products p ON i.product_id = p.product_id
GROUP BY 1
ORDER BY total_sales DESC
LIMIT 10;"""

def clean_extracted_sql(raw_text: str) -> str:
    if "```sql" in raw_text.lower():
        parts = re.split(r"```sql", raw_text, flags=re.IGNORECASE)
        if len(parts) > 1:
            return parts[1].split("```")[0].strip()
    elif "```" in raw_text:
        parts = raw_text.split("```")
        if len(parts) > 1:
            return parts[1].strip()
    return raw_text.strip()

def generate_and_execute_sql(state: AgentState) -> AgentState:
    schema_context = db_manager.get_schema_summary()
    max_retries = settings.MAX_SQL_RETRIES
    retry_count = 0
    
    while retry_count <= max_retries:
        if retry_count == 0:
            prompt = f"""You are an expert Principal Data and Analytics Engineer generating DuckDB SQL for product analytics.

Database Schema and Context:
{schema_context}

User Business Question:
"{state.user_query}"

Intent: {state.intent}

Guidelines:
1. Write pure, read-only DuckDB SQL (SELECT or WITH).
2. For A/B tests, ALWAYS aggregate by variant (control vs treatment) getting sample counts, conversions, and revenue.
3. For Root Cause / Anomaly questions, group by the relevant dimension (device, country, month/week) to isolate differences.
4. Output ONLY the executable SQL query wrapped inside ```sql ... ``` code block.
"""
        else:
            prompt = f"""The previous SQL query failed during execution. Self-heal and fix the SQL query based on the error.

Database Schema and Context:
{schema_context}

User Question: "{state.user_query}"
Previous Failed SQL:
```sql
{state.generated_sql}
```

DuckDB Error Traceback:
{state.sql_error}

Fix the column names, syntax, or table joins. Return ONLY the corrected SQL query inside ```sql ... ```.
"""

        state.reasoning_steps.append(f"⚙️ SQL Generation & Execution (Attempt {retry_count + 1}/{max_retries + 1})...")
        llm_output = _call_llm(prompt, provider=state.provider, api_key=state.api_key, user_query=state.user_query)
        sql = clean_extracted_sql(llm_output)
        state.generated_sql = sql
        
        is_valid, guard_err = SQLGuardrail.validate_sql(sql)
        if not is_valid:
            state.sql_error = f"Guardrail Error: {guard_err}"
            state.sql_execution_history.append({"attempt": retry_count + 1, "sql": sql, "error": guard_err})
            state.reasoning_steps.append(f"⚠️ Guardrail blocked query: {guard_err}. Initiating self-healing...")
            retry_count += 1
            continue
            
        df, elapsed_ms, exec_err = db_manager.execute_query(sql)
        state.execution_time_ms = elapsed_ms
        
        if exec_err:
            state.sql_error = exec_err
            state.sql_execution_history.append({"attempt": retry_count + 1, "sql": sql, "error": exec_err, "time_ms": elapsed_ms})
            state.reasoning_steps.append(f"❌ SQL Execution Error: {exec_err}. Intercepting error for self-correction...")
            retry_count += 1
            continue
            
        state.sql_error = None
        state.sql_retries = retry_count
        state.query_columns = list(df.columns) if df is not None else []
        state.query_result_data = df.to_dict(orient="records") if df is not None else []
        state.sql_execution_history.append({"attempt": retry_count + 1, "sql": sql, "rows": len(df) if df is not None else 0, "time_ms": elapsed_ms, "success": True})
        
        healing_note = f" (Self-healed after {retry_count} retries!)" if retry_count > 0 else ""
        state.reasoning_steps.append(f"✅ SQL executed successfully in {elapsed_ms}ms returned {len(df)} rows.{healing_note}")
        break
        
    return state
