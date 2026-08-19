import os
import random
import datetime
import duckdb
import numpy as np
import pandas as pd

def generate_mock_data(db_path: str, user_count: int = 8000, seed: int = 42):
    np.random.seed(seed)
    random.seed(seed)
    
    print(f'Generating mock e-commerce & A/B testing dataset for DuckDB: {db_path}')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 1. Users Table
    user_ids = [f'usr_{i:06d}' for i in range(1, user_count + 1)]
    countries = ['US', 'UK', 'DE', 'IN', 'CA', 'FR']
    country_weights = [0.40, 0.18, 0.12, 0.15, 0.08, 0.07]
    devices = ['mobile_android', 'mobile_ios', 'desktop']
    device_weights = [0.45, 0.35, 0.20]
    channels = ['organic_search', 'paid_social', 'email', 'referral', 'direct']
    channel_weights = [0.30, 0.25, 0.20, 0.15, 0.10]
    segments = ['new', 'active', 'churn_risk', 'vip']
    segment_weights = [0.25, 0.50, 0.18, 0.07]
    
    start_date = datetime.date(2025, 1, 1)
    end_date = datetime.date(2025, 12, 31)
    days_range = (end_date - start_date).days
    
    signup_dates = [start_date + datetime.timedelta(days=random.randint(0, days_range)) for _ in range(user_count)]
    
    users_df = pd.DataFrame({
        'user_id': user_ids,
        'signup_date': signup_dates,
        'country': np.random.choice(countries, size=user_count, p=country_weights),
        'primary_device': np.random.choice(devices, size=user_count, p=device_weights),
        'acquisition_channel': np.random.choice(channels, size=user_count, p=channel_weights),
        'user_segment': np.random.choice(segments, size=user_count, p=segment_weights)
    })
    
    # 2. Sessions Table (avg ~3.5 sessions per user)
    session_count = user_count * 4
    session_user_ids = np.random.choice(user_ids, size=session_count)
    session_ids = [f'ses_{i:07d}' for i in range(1, session_count + 1)]
    
    session_starts = []
    for uid in session_user_ids:
        # Session happens after signup
        u_signup = users_df.loc[users_df['user_id'] == uid, 'signup_date'].values[0]
        if isinstance(u_signup, np.datetime64):
            u_signup = pd.to_datetime(u_signup).date()
        offset_days = random.randint(0, min(90, (end_date - u_signup).days if (end_date - u_signup).days > 0 else 0))
        s_date = u_signup + datetime.timedelta(days=offset_days)
        s_time = datetime.datetime(s_date.year, s_date.month, s_date.day, 
                                   random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))
        session_starts.append(s_time)
        
    landing_pages = ['home', 'category_page', 'product_detail', 'promo_landing']
    
    sessions_df = pd.DataFrame({
        'session_id': session_ids,
        'user_id': session_user_ids,
        'session_start': session_starts,
        'landing_page': np.random.choice(landing_pages, size=session_count, p=[0.4, 0.3, 0.2, 0.1]),
        'session_duration_sec': np.random.exponential(scale=180, size=session_count).astype(int) + 15,
        'page_views': np.random.poisson(lam=4.2, size=session_count) + 1,
        'device': np.random.choice(devices, size=session_count, p=device_weights)
    })
    
    # 3. Events Table (Funnel: view_item -> add_to_cart -> start_checkout -> purchase)
    events_list = []
    categories = ['Electronics', 'Apparel', 'Home & Kitchen', 'Beauty', 'Sports']
    cat_price_range = {
        'Electronics': (40.0, 450.0),
        'Apparel': (15.0, 120.0),
        'Home & Kitchen': (25.0, 200.0),
        'Beauty': (10.0, 80.0),
        'Sports': (20.0, 150.0)
    }
    
    event_counter = 1
    for row in sessions_df.itertuples():
        s_id = row.session_id
        u_id = row.user_id
        s_time = row.session_start
        s_device = row.device
        
        # Step 1: view_item
        cat = random.choice(categories)
        price = round(random.uniform(*cat_price_range[cat]), 2)
        events_list.append({
            'event_id': f'evt_{event_counter:08d}',
            'session_id': s_id,
            'user_id': u_id,
            'event_type': 'view_item',
            'event_timestamp': s_time,
            'device': s_device,
            'category': cat,
            'item_price': price,
            'revenue': 0.0
        })
        event_counter += 1
        
        # Step 2: add_to_cart (55% probability)
        if random.random() < 0.55:
            events_list.append({
                'event_id': f'evt_{event_counter:08d}',
                'session_id': s_id,
                'user_id': u_id,
                'event_type': 'add_to_cart',
                'event_timestamp': s_time + datetime.timedelta(seconds=random.randint(10, 60)),
                'device': s_device,
                'category': cat,
                'item_price': price,
                'revenue': 0.0
            })
            event_counter += 1
            
            # Step 3: start_checkout (60% of cart additions)
            if random.random() < 0.60:
                events_list.append({
                    'event_id': f'evt_{event_counter:08d}',
                    'session_id': s_id,
                    'user_id': u_id,
                    'event_type': 'start_checkout',
                    'event_timestamp': s_time + datetime.timedelta(seconds=random.randint(70, 150)),
                    'device': s_device,
                    'category': cat,
                    'item_price': price,
                    'revenue': 0.0
                })
                event_counter += 1
                
                # Step 4: purchase
                # Base conversion rate ~48%
                # Anomaly: Android in Q3 (July-Sept 2025) has checkout drop to 15% due to simulated payment gateway bug!
                is_q3_android = (s_device == 'mobile_android' and s_time.month in [7, 8, 9])
                purchase_prob = 0.15 if is_q3_android else 0.52
                
                if random.random() < purchase_prob:
                    qty = random.choices([1, 2, 3], weights=[0.75, 0.20, 0.05])[0]
                    total_rev = round(price * qty, 2)
                    events_list.append({
                        'event_id': f'evt_{event_counter:08d}',
                        'session_id': s_id,
                        'user_id': u_id,
                        'event_type': 'purchase',
                        'event_timestamp': s_time + datetime.timedelta(seconds=random.randint(160, 300)),
                        'device': s_device,
                        'category': cat,
                        'item_price': price,
                        'revenue': total_rev
                    })
                    event_counter += 1
                    
    events_df = pd.DataFrame(events_list)
    
    # 4. Experiments Table
    # Exp 1: exp_checkout_redesign_101 (Clean A/B, 5000 users, 50/50 split, Lift: 14.8% vs 12.2%, Statistically Significant)
    exp1_users = user_ids[:5000]
    exp1_variants = ['control' if i % 2 == 0 else 'treatment' for i in range(5000)]
    exp1_converts = [
        1 if (v == 'control' and random.random() < 0.122) or (v == 'treatment' and random.random() < 0.149) else 0
        for v in exp1_variants
    ]
    exp1_rev = [round(random.uniform(45.0, 180.0), 2) if c == 1 else 0.0 for c in exp1_converts]
    
    exp1_df = pd.DataFrame({
        'experiment_id': ['exp_checkout_redesign_101'] * 5000,
        'user_id': exp1_users,
        'variant': exp1_variants,
        'assigned_at': [datetime.datetime(2025, 4, 1, 10, 0, 0) + datetime.timedelta(hours=i) for i in range(5000)],
        'converted': exp1_converts,
        'revenue': exp1_rev
    })
    
    # Exp 2: exp_onboarding_gamify_102 (Flat A/B, 4000 users, 50/50 split, No Lift: 8.2% vs 8.4%, Inconclusive p=0.78)
    exp2_users = user_ids[2000:6000]
    exp2_variants = ['control' if i % 2 == 0 else 'treatment' for i in range(4000)]
    exp2_converts = [
        1 if (v == 'control' and random.random() < 0.082) or (v == 'treatment' and random.random() < 0.084) else 0
        for v in exp2_variants
    ]
    exp2_rev = [round(random.uniform(20.0, 95.0), 2) if c == 1 else 0.0 for c in exp2_converts]
    
    exp2_df = pd.DataFrame({
        'experiment_id': ['exp_onboarding_gamify_102'] * 4000,
        'user_id': exp2_users,
        'variant': exp2_variants,
        'assigned_at': [datetime.datetime(2025, 6, 1, 9, 0, 0) + datetime.timedelta(hours=i) for i in range(4000)],
        'converted': exp2_converts,
        'revenue': exp2_rev
    })
    
    # Exp 3: exp_ai_search_rank_103 (Has deliberate Sample Ratio Mismatch: 3500 Control vs 1500 Treatment, SRM p < 0.0001)
    exp3_users = user_ids[1000:6000]
    exp3_variants = ['control' if random.random() < 0.70 else 'treatment' for _ in range(5000)]
    exp3_converts = [
        1 if (v == 'control' and random.random() < 0.140) or (v == 'treatment' and random.random() < 0.185) else 0
        for v in exp3_variants
    ]
    exp3_rev = [round(random.uniform(50.0, 220.0), 2) if c == 1 else 0.0 for c in exp3_converts]
    
    exp3_df = pd.DataFrame({
        'experiment_id': ['exp_ai_search_rank_103'] * 5000,
        'user_id': exp3_users,
        'variant': exp3_variants,
        'assigned_at': [datetime.datetime(2025, 10, 1, 8, 0, 0) + datetime.timedelta(hours=i) for i in range(5000)],
        'converted': exp3_converts,
        'revenue': exp3_rev
    })
    
    experiments_df = pd.concat([exp1_df, exp2_df, exp3_df], ignore_index=True)
    
    # Save into DuckDB
    con = duckdb.connect(db_path)
    con.execute('CREATE OR REPLACE TABLE users AS SELECT * FROM users_df')
    con.execute('CREATE OR REPLACE TABLE sessions AS SELECT * FROM sessions_df')
    con.execute('CREATE OR REPLACE TABLE events AS SELECT * FROM events_df')
    con.execute('CREATE OR REPLACE TABLE experiments AS SELECT * FROM experiments_df')
    
    print(f'Database populated successfully!')
    print(f'  - Users: {len(users_df):,} rows')
    print(f'  - Sessions: {len(sessions_df):,} rows')
    print(f'  - Events: {len(events_df):,} rows')
    print(f'  - Experiments: {len(experiments_df):,} rows')
    con.close()

if __name__ == '__main__':
    default_path = os.path.join(os.path.dirname(__file__), 'analytics.duckdb')
    generate_mock_data(default_path)
