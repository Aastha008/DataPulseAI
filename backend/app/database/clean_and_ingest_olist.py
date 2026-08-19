import os
import glob
import time
import duckdb
import pandas as pd
import numpy as np

def clean_and_ingest_olist(dataset_dir: str, db_path: str):
    print(f"[PIPELINE] Starting Automated Data Cleaning & Ingestion Pipeline for Real Olist Dataset...")
    start_time = time.time()
    
    # 1. Category Translation Map
    trans_file = os.path.join(dataset_dir, "product_category_name_translation.csv")
    if os.path.exists(trans_file):
        df_trans = pd.read_csv(trans_file)
        cat_map = dict(zip(df_trans["product_category_name"], df_trans["product_category_name_english"]))
    else:
        cat_map = {}

    # 2. Clean Customers Dataset
    print("[CLEANING] Customers dataset...")
    cust_file = os.path.join(dataset_dir, "olist_customers_dataset.csv")
    df_cust = pd.read_csv(cust_file)
    df_cust["customer_city"] = df_cust["customer_city"].str.title().fillna("Unknown")
    df_cust["customer_state"] = df_cust["customer_state"].str.upper().fillna("UN")
    
    # 3. Clean Products Dataset
    print("[CLEANING] Products & translating categories to English...")
    prod_file = os.path.join(dataset_dir, "olist_products_dataset.csv")
    df_prod = pd.read_csv(prod_file)
    df_prod["product_category_name_english"] = df_prod["product_category_name"].map(cat_map).fillna("general_merchandise")
    df_prod["product_weight_g"] = df_prod["product_weight_g"].fillna(df_prod["product_weight_g"].median())
    
    # 4. Clean Orders Dataset
    print("[CLEANING] Orders dataset & parsing timestamps...")
    orders_file = os.path.join(dataset_dir, "olist_orders_dataset.csv")
    df_orders = pd.read_csv(orders_file)
    
    date_cols = [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ]
    for col in date_cols:
        df_orders[col] = pd.to_datetime(df_orders[col], errors="coerce")
        
    df_orders["delivery_days"] = (df_orders["order_delivered_customer_date"] - df_orders["order_purchase_timestamp"]).dt.total_seconds() / 86400.0
    df_orders["estimated_delivery_days"] = (df_orders["order_estimated_delivery_date"] - df_orders["order_purchase_timestamp"]).dt.total_seconds() / 86400.0
    df_orders["is_delayed"] = np.where(df_orders["order_delivered_customer_date"] > df_orders["order_estimated_delivery_date"], 1, 0)
    df_orders["order_status"] = df_orders["order_status"].fillna("delivered")

    # 5. Clean Order Items Dataset
    print("[CLEANING] Order Items & calculating line items...")
    items_file = os.path.join(dataset_dir, "olist_order_items_dataset.csv")
    df_items = pd.read_csv(items_file)
    df_items["shipping_limit_date"] = pd.to_datetime(df_items["shipping_limit_date"], errors="coerce")
    df_items["price"] = df_items["price"].fillna(0.0)
    df_items["freight_value"] = df_items["freight_value"].fillna(0.0)
    df_items["total_item_value"] = df_items["price"] + df_items["freight_value"]

    # 6. Clean Payments Dataset
    print("[CLEANING] Order Payments dataset...")
    pay_file = os.path.join(dataset_dir, "olist_order_payments_dataset.csv")
    df_pay = pd.read_csv(pay_file)
    df_pay["payment_type"] = df_pay["payment_type"].replace({"not_defined": "other"}).fillna("credit_card")
    df_pay["payment_installments"] = df_pay["payment_installments"].clip(lower=1)
    df_pay["payment_value"] = df_pay["payment_value"].fillna(0.0)

    # 7. Clean Reviews Dataset
    print("[CLEANING] Order Reviews dataset...")
    rev_file = os.path.join(dataset_dir, "olist_order_reviews_dataset.csv")
    df_rev = pd.read_csv(rev_file)
    df_rev["review_score"] = pd.to_numeric(df_rev["review_score"], errors="coerce").fillna(5).astype(int)
    df_rev["review_comment_title"] = df_rev["review_comment_title"].fillna("")
    df_rev["review_comment_message"] = df_rev["review_comment_message"].fillna("")
    df_rev["review_creation_date"] = pd.to_datetime(df_rev["review_creation_date"], errors="coerce")

    # Ingest into DuckDB
    print(f"[DATABASE] Loading cleaned datasets into DuckDB: {db_path}")
    con = duckdb.connect(db_path)
    
    con.execute("CREATE OR REPLACE TABLE olist_orders AS SELECT * FROM df_orders")
    con.execute("CREATE OR REPLACE TABLE olist_order_items AS SELECT * FROM df_items")
    con.execute("CREATE OR REPLACE TABLE olist_order_payments AS SELECT * FROM df_pay")
    con.execute("CREATE OR REPLACE TABLE olist_order_reviews AS SELECT * FROM df_rev")
    con.execute("CREATE OR REPLACE TABLE olist_customers AS SELECT * FROM df_cust")
    con.execute("CREATE OR REPLACE TABLE olist_products AS SELECT * FROM df_prod")
    
    print("\n[SUCCESS] Automated Data Ingestion Complete!")
    print(f"  - olist_orders: {len(df_orders):,} rows")
    print(f"  - olist_order_items: {len(df_items):,} rows")
    print(f"  - olist_order_payments: {len(df_pay):,} rows")
    print(f"  - olist_order_reviews: {len(df_rev):,} rows")
    print(f"  - olist_customers: {len(df_cust):,} rows")
    print(f"  - olist_products: {len(df_prod):,} rows")
    print(f"[RUNTIME] Total Pipeline Execution Time: {time.time() - start_time:.2f} seconds")
    con.close()

if __name__ == "__main__":
    import kagglehub
    path = kagglehub.dataset_download("olistbr/brazilian-ecommerce")
    db_file = os.path.join(os.path.dirname(__file__), "analytics.duckdb")
    clean_and_ingest_olist(path, db_file)
