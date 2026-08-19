# DataPulse Analytics: Autonomous Product Analytics, Experimentation & Root-Cause Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0+-FFF000?style=flat&logo=duckdb&logoColor=black)](https://duckdb.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)

**DataPulse Analytics** is an autonomous analytics and experimentation platform that investigates product metrics, isolates root-cause anomalies, and executes deterministic A/B testing analysis across 547,000+ real-world e-commerce transaction records.

---

## Key Capabilities

1. **Self-Healing SQL Engine**: Generates DuckDB SQL from natural language business questions with automatic schema reflection and error-recovery retry loops.
2. **Deterministic Statistical Rigor**: Computes two-proportion z-tests, 95% confidence intervals, and Sample Ratio Mismatch (SRM) Chi-square tests with SciPy.
3. **Automated Evaluation Benchmark Suite (`evals/`)**: Golden dataset tests verifying SQL precision, statistical calculations, and security guardrails.
4. **Real-World Enterprise Scale**: Tested against 547,000+ real Kaggle Brazilian E-Commerce (Olist) records and multi-stage funnel logs.

---

## System Architecture

```
User Business Question
         │
         ▼
┌────────────────────────────────────────────────────────┐
│              Analytics Multi-Agent Pipeline            │
│                                                        │
│  1. Intent Classifier (A/B Test | Root Cause | Funnel) │
│  2. DuckDB Text-to-SQL + Self-Correction Loop          │
│  3. SciPy Deterministic Statistical Engine             │
│  4. Executive Briefing & Interactive Plotly Charts     │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
  FastAPI Backend (Port 8000) & Streamlit UI (Port 8501)
```

---

## Quickstart

### 1. Installation
```bash
git clone https://github.com/your-username/datapulse-ai.git
cd datapulse-ai
pip install -r requirements.txt
```

### 2. Launch the Streamlit App
```bash
python -m streamlit run frontend/app.py
```

### 3. Run Automated Tests
```bash
python -m pytest evals/test_benchmarks.py -v
```

---

## Deployment Options

### Option A: Free 1-Click Streamlit Community Cloud (Recommended)
1. Push this repository to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
3. Click **"New App"** and select:
   * **Repository**: `your-username/datapulse-ai`
   * **Branch**: `main`
   * **Main file path**: `frontend/app.py`
4. Click **Deploy!**

### Option B: Docker Container
```bash
docker-compose up --build
```

---

