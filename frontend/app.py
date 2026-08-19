import os
import sys
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Reload modules to purge in-memory cache
import importlib
from backend.app.agents import insight_generator, sql_agent, graph
importlib.reload(insight_generator)
importlib.reload(sql_agent)
importlib.reload(graph)

from backend.app.config import settings
from backend.app.database.db import db_manager
from backend.app.agents.state import AgentState
from backend.app.agents.graph import agent_workflow
from backend.app.agents.stats_engine import stats_engine

st.set_page_config(
    page_title="DataPulse Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .app-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    .app-subtitle {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 1.4rem;
    }
    .metric-badge {
        display: inline-block;
        background-color: #F1F5F9;
        color: #334155;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .empty-state {
        background-color: #F8FAFC;
        border: 1px dashed #CBD5E1;
        border-radius: 8px;
        padding: 32px 24px;
        text-align: center;
        color: #64748B;
        margin-top: 24px;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### **DataPulse Analytics**")
    st.caption("Product Analytics & Experimentation Platform")
    
    st.divider()
    st.markdown("**LLM Provider**")
    provider = st.selectbox("Select Model Provider", ["gemini", "openai", "groq", "mock (offline)"], index=0, label_visibility="collapsed")
    
    api_key = None
    if provider != "mock (offline)":
        api_key = st.text_input(f"{provider.capitalize()} API Key", type="password", placeholder="Enter key (or uses .env)")
        
    st.divider()
    st.markdown("**Connected Database**")
    st.markdown("`DuckDB (In-Memory Engine)`")
    st.caption("547,000+ real Kaggle e-commerce & A/B testing records loaded.")

st.markdown('<div class="app-title">DataPulse Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Self-serve product analytics, statistical hypothesis testing, and root-cause analysis.</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Analytics & Insights", "A/B Testing Lab", "Data Catalog & SQL Editor"])

PRESET_QUESTIONS = [
    "What are the top 5 product categories by total sales in Olist?",
    "How do delivery delays impact customer review scores in Olist?",
    "Rank payment methods by average order value in Olist",
    "Which Brazilian states have the highest e-commerce revenue?",
    "What is the monthly order trend over time in Olist?",
    "Evaluate A/B test for exp_checkout_redesign_101 with 95% CI and lift",
    "Check exp_ai_search_rank_103 for Sample Ratio Mismatch (SRM)",
    "Why did checkout conversion drop in mobile devices during Q3?",
    "Show the full e-commerce conversion funnel drop-off"
]

with tab1:
    st.markdown("##### **Explore Metrics & Business Questions**")
    
    selected_option = st.selectbox(
        "Choose a sample query or select 'Custom Question':",
        ["Custom Question"] + PRESET_QUESTIONS,
        index=1,
        label_visibility="collapsed"
    )
    
    if selected_option == "Custom Question":
        current_question = st.text_input("Enter your question:", value="What are the top 5 product categories by total sales in Olist?")
    else:
        current_question = selected_option
        st.markdown(f"<span class='metric-badge'>Selected Question</span> *{current_question}*", unsafe_allow_html=True)

    st.write("")
    col_run, _ = st.columns([2, 5])
    with col_run:
        execute_query = st.button("Run Analysis", type="primary", use_container_width=True)

    # ONLY run when the user explicitly clicks the "Run Analysis" button!
    if execute_query:
        with st.spinner("Analyzing data and calculating metrics..."):
            init_state = AgentState(
                user_query=current_question,
                provider=provider.replace(" (offline)", ""),
                api_key=api_key
            )
            final_state = agent_workflow.run(init_state)
            st.session_state["active_analysis"] = final_state

    output = st.session_state.get("active_analysis")
    
    if output:
        st.write("")
        st.markdown(f"<span class='metric-badge'>Query Latency: {output.execution_time_ms} ms</span> <span class='metric-badge'>Intent: {output.intent}</span> <span class='metric-badge'>Rows: {len(output.query_result_data)}</span>", unsafe_allow_html=True)
        st.write("")

        # 1. Visualization
        if output.plotly_chart_spec:
            spec = output.plotly_chart_spec
            
            if spec["type"] == "funnel":
                fig = go.Figure(go.Funnel(
                    y=spec["stages"],
                    x=spec["values"],
                    textinfo="value+percent initial",
                    marker={"color": ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD"]}
                ))
                fig.update_layout(
                    title=spec.get("title", "Funnel Drop-off"),
                    template="plotly_white",
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=380
                )
                st.plotly_chart(fig, use_container_width=True)
                
            elif spec["type"] == "line":
                df_chart = pd.DataFrame({"x": spec["x"], "y": spec["y"]})
                fig = px.line(
                    df_chart, x="x", y="y", markers=True,
                    title=spec.get("title", ""),
                    labels={"x": spec.get("xaxis_title", ""), "y": spec.get("yaxis_title", "")},
                    template="plotly_white"
                )
                fig.update_traces(line_color="#2563EB", line_width=3, marker=dict(size=7, color="#1D4ED8"))
                fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=380)
                st.plotly_chart(fig, use_container_width=True)
                
            elif spec["type"] == "bar":
                df_chart = pd.DataFrame({"x": spec["x"], "y": spec["y"]})
                fig = px.bar(
                    df_chart, x="x", y="y",
                    title=spec.get("title", ""),
                    labels={"x": spec.get("xaxis_title", ""), "y": spec.get("yaxis_title", "")},
                    template="plotly_white",
                    color_discrete_sequence=["#2563EB"]
                )
                fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=380)
                st.plotly_chart(fig, use_container_width=True)

        # 2. Key Takeaways & Recommendations
        st.markdown(output.executive_memo)
        
        # 3. Technical Breakdown Accordion
        with st.expander("View Generated SQL & Execution Steps", expanded=False):
            st.markdown("**DuckDB SQL Query:**")
            st.code(output.generated_sql, language="sql")
            st.markdown("**Calculation Steps:**")
            for step in output.reasoning_steps:
                st.markdown(f"- {step}")

        st.download_button(
            label="Download Report (.md)",
            data=output.executive_memo,
            file_name="analytics_report.md",
            mime="text/markdown"
        )
    else:
        st.markdown("""
        <div class="empty-state">
            <div style="font-size: 1.05rem; font-weight: 600; color: #334155; margin-bottom: 6px;">Ready to Analyze</div>
            <div>Select or type a business question above, then click <b>Run Analysis</b> to query DuckDB and generate insights.</div>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.markdown("##### **A/B Testing & Statistical Significance Calculator**")
    st.caption("Perform two-proportion z-tests, confidence interval estimates, and Sample Ratio Mismatch (SRM) checks.")
    
    col_c, col_t = st.columns(2)
    with col_c:
        st.markdown("**Control Group (A)**")
        c_sample = st.number_input("Visitors / Sample Size", min_value=10, value=2500, step=100, key="c_samp")
        c_conv = st.number_input("Conversions", min_value=0, value=305, step=10, key="c_conv")
        c_rate = (c_conv / c_sample) * 100.0 if c_sample > 0 else 0
        st.metric("Baseline Rate", f"{c_rate:.2f}%")
        
    with col_t:
        st.markdown("**Treatment Group (B)**")
        t_sample = st.number_input("Visitors / Sample Size", min_value=10, value=2500, step=100, key="t_samp")
        t_conv = st.number_input("Conversions", min_value=0, value=370, step=10, key="t_conv")
        t_rate = (t_conv / t_sample) * 100.0 if t_sample > 0 else 0
        st.metric("Test Rate", f"{t_rate:.2f}%")
        
    st.write("")
    if st.button("Calculate Significance", type="primary"):
        ab_calc = stats_engine.calculate_ab_test(c_conv, c_sample, t_conv, t_sample)
        srm_calc = stats_engine.check_sample_ratio_mismatch(c_sample, t_sample)
        
        if srm_calc["srm_detected"]:
            st.error(f"Sample Ratio Mismatch detected (p = {srm_calc['p_value']:.5f} < 0.01). The sample split appears biased. Do not make ship decisions based on this test.")
        else:
            st.success(f"Sample ratio is balanced (p = {srm_calc['p_value']:.4f} >= 0.01). Traffic split is healthy.")
            
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Relative Lift", f"{ab_calc['relative_lift_pct']}%", delta=f"{ab_calc['relative_lift_pct']}%")
        m2.metric("p-value", f"{ab_calc['p_value']:.5f}")
        m3.metric("Z-Score", f"{ab_calc['z_score']}")
        m4.metric("95% CI on Diff", f"[{ab_calc['confidence_interval_95'][0]}%, {ab_calc['confidence_interval_95'][1]}%]")
        
        st.info(f"**Recommendation**: {ab_calc['recommendation']}")

with tab3:
    st.markdown("##### **Data Catalog & Raw Tables**")
    tables = [
        "olist_orders", "olist_order_items", "olist_order_payments",
        "olist_order_reviews", "olist_customers", "olist_products",
        "experiments", "events", "users"
    ]
    selected_tbl = st.selectbox("Choose Table to Inspect", tables)
    
    df_preview, elapsed, err = db_manager.execute_query(f"SELECT * FROM {selected_tbl} LIMIT 100")
    if err:
        st.error(err)
    else:
        st.dataframe(df_preview, use_container_width=True)
        st.caption(f"Showing first 100 rows (Retrieved in {elapsed} ms).")
        
    st.divider()
    st.markdown("##### **SQL Query Editor**")
    custom_sql = st.text_area(
        "Run custom DuckDB SQL (read-only):",
        value="SELECT p.product_category_name_english AS category, COUNT(i.order_id) AS total_orders, ROUND(SUM(i.price), 2) AS total_sales FROM olist_order_items i JOIN olist_products p ON i.product_id = p.product_id GROUP BY 1 ORDER BY total_sales DESC LIMIT 10;",
        height=100
    )
    if st.button("Execute Query"):
        df_custom, el_custom, err_custom = db_manager.execute_query(custom_sql)
        if err_custom:
            st.error(err_custom)
        else:
            st.success(f"Returned {len(df_custom)} rows in {el_custom} ms.")
            st.dataframe(df_custom, use_container_width=True)
