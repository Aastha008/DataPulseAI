import os
import time
import duckdb
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from ..config import settings
from .seed_data import generate_mock_data

class DatabaseManager:
    _instance = None
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._ensure_database_exists()
        
    def _ensure_database_exists(self):
        if not os.path.exists(self.db_path) or os.path.getsize(self.db_path) == 0:
            print(f"DuckDB file not found at {self.db_path}. Seeding initial data...")
            generate_mock_data(self.db_path)
            
    def get_connection(self):
        return duckdb.connect(self.db_path, read_only=False)

    def execute_query(self, sql: str) -> Tuple[Optional[pd.DataFrame], float, Optional[str]]:
        start_time = time.time()
        try:
            con = self.get_connection()
            df = con.execute(sql).df()
            elapsed_ms = (time.time() - start_time) * 1000.0
            con.close()
            return df, round(elapsed_ms, 2), None
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000.0
            return None, round(elapsed_ms, 2), str(e)

    def get_schema_summary(self) -> str:
        con = self.get_connection()
        tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
        
        schema_text = []
        for (tbl,) in tables:
            columns_info = con.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{tbl}'").fetchall()
            row_count = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            sample_rows = con.execute(f"SELECT * FROM {tbl} LIMIT 2").df().to_dict(orient='records')
            
            cols_str = ', '.join([f"{c} ({t})" for c, t in columns_info])
            schema_text.append(f"### Table: `{tbl}` ({row_count:,} rows)")
            schema_text.append(f"- Columns: {cols_str}")
            schema_text.append(f"- Sample Data: {sample_rows}")
            schema_text.append("")
            
        con.close()
        
        glossary = """### Business Semantic Glossary & Key Analytical Tables:
1. Real Kaggle E-Commerce (Olist):
   - `olist_orders`: (order_id, customer_id, order_status, order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date, delivery_days, is_delayed)
   - `olist_order_items`: (order_id, order_item_id, product_id, seller_id, price, freight_value, total_item_value)
   - `olist_order_payments`: (order_id, payment_sequential, payment_type [credit_card, boleto, voucher, debit_card], payment_installments, payment_value)
   - `olist_order_reviews`: (review_id, order_id, review_score [1 to 5], review_comment_title, review_comment_message, review_creation_date)
   - `olist_customers`: (customer_id, customer_unique_id, customer_city, customer_state)
   - `olist_products`: (product_id, product_category_name_english, product_weight_g)

2. A/B Testing & Funnel Tables:
   - `experiments`: (experiment_id, user_id, variant [control vs treatment], assigned_at, converted, revenue)
   - `events`: (event_id, session_id, user_id, event_type, event_timestamp, device, category, item_price, revenue)
   - `users`: (user_id, signup_date, country, primary_device, acquisition_channel, user_segment)
"""
        return "\n".join(schema_text) + "\n" + glossary

db_manager = DatabaseManager()
