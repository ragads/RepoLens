import pandas as pd
import numpy as np
import os

def generate_synthetic_data(output_path='data/raw_transactions.csv', n_rows=284807):
    print(f"Generating {n_rows} synthetic transactions...")
    np.random.seed(42)
    
    # Simulate Time (0 to 172792 seconds - 2 days)
    time = np.sort(np.random.randint(0, 172792, n_rows))
    
    # Simulate V1-V28 (PCA components, normally distributed)
    v_features = {f'V{i}': np.random.normal(0, 1, n_rows) for i in range(1, 29)}
    
    # Simulate Amount (Log-normal distribution to look like real transaction amounts)
    amount = np.random.lognormal(mean=2, sigma=1, size=n_rows)
    
    # Simulate Class (0: Normal, 1: Fraud) - Highly imbalanced
    # Real dataset has ~0.172% fraud
    is_fraud = np.random.choice([0, 1], size=n_rows, p=[0.998, 0.002])
    
    # Create DataFrame
    df = pd.DataFrame({
        'Time': time,
        **v_features,
        'Amount': amount,
        'Class': is_fraud
    })
    
    # Simulate UserID (Not in original Kaggle dataset, but needed for 'Txn_per_hour' requirement)
    # Let's assume 10,000 unique users
    user_ids = np.random.randint(1000, 11000, n_rows)
    df['UserID'] = user_ids
    
    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved synthetic dataset to {output_path}")

if __name__ == "__main__":
    generate_synthetic_data()
