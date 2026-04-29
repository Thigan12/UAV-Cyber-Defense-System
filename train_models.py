import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import tensorflow as tf
from tensorflow.keras.models import Sequential # type: ignore
from tensorflow.keras.layers import LSTM, Dense, Dropout # type: ignore

def preprocess_data(file_path):
    print("Loading data...")
    df = pd.read_csv(file_path)
    
    # Forward fill and backward fill to handle sparse MAVLink data
    print("Forward-filling sparse sensor data...")
    df = df.ffill().bfill()
    
    # Drop non-numeric or irrelevant columns for training
    df = df.drop(columns=['timestamp', 'msg_type', 'type', 'autopilot', 'base_mode', 'system_status', 'custom_mode'], errors='ignore')
    
    # Ensure everything is numeric
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.fillna(0) # Catch any remaining NaNs
    
    y = df['label'].values
    X = df.drop(columns=['label']).values
    
    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Save the scaler for Phase 3 (live dashboard)
    with open('scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
        
    return X_scaled, y

def create_sequences(X, y, time_steps=10):
    """Reshape data for LSTM (samples, time_steps, features)"""
    Xs, ys = [], []
    for i in range(len(X) - time_steps):
        Xs.append(X[i:(i + time_steps)])
        ys.append(y[i + time_steps])
    return np.array(Xs), np.array(ys)

def build_lstm(input_shape):
    model = Sequential([
        LSTM(64, input_shape=input_shape, return_sequences=True),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

def train_and_evaluate():
    X_scaled, y = preprocess_data('combined_dataset.csv')
    print(f"Data preprocessed. X shape: {X_scaled.shape}, y shape: {y.shape}")
    
    # ---------------------------------------------------------
    # Baseline 1: Random Forest (Non-temporal)
    # ---------------------------------------------------------
    print("\n--- Training Random Forest Baseline ---")
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
    rf = RandomForestClassifier(n_estimators=50, random_state=42)
    rf.fit(X_train, y_train)
    rf_preds = rf.predict(X_test)
    print("Random Forest Accuracy:", accuracy_score(y_test, rf_preds))
    print(classification_report(y_test, rf_preds))
    with open('rf_model.pkl', 'wb') as f:
        pickle.dump(rf, f)
        
    # ---------------------------------------------------------
    # LSTM with 5-Fold Cross Validation
    # ---------------------------------------------------------
    print("\n--- Training LSTM with 5-Fold CV ---")
    TIME_STEPS = 10
    X_seq, y_seq = create_sequences(X_scaled, y, TIME_STEPS)
    
    kfold = KFold(n_splits=5, shuffle=True, random_state=42)
    fold_no = 1
    cv_scores = []
    
    # For demonstration, we'll train fully on the first fold, and just score the rest to save time
    for train, test in kfold.split(X_seq, y_seq):
        print(f"Training Fold {fold_no}...")
        model = build_lstm((X_seq.shape[1], X_seq.shape[2]))
        
        # Train for 5 epochs (keep it fast for demonstration)
        model.fit(X_seq[train], y_seq[train], epochs=5, batch_size=64, verbose=0)
        
        scores = model.evaluate(X_seq[test], y_seq[test], verbose=0)
        print(f"Score for fold {fold_no}: {model.metrics_names[1]} of {scores[1]*100:.2f}%")
        cv_scores.append(scores[1] * 100)
        
        if fold_no == 1:
            # Save the model from the first fold
            model.save('lstm_uav_model.h5')
            
        fold_no += 1
        
    print(f"\nLSTM 5-Fold CV Average Accuracy: {np.mean(cv_scores):.2f}% (+/- {np.std(cv_scores):.2f}%)")

if __name__ == '__main__':
    train_and_evaluate()
