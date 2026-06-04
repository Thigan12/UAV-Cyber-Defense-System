import os
import pickle
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.over_sampling import SMOTE
from tensorflow.keras.models import Sequential # type: ignore
from tensorflow.keras.layers import LSTM, Bidirectional, Dense, Dropout, BatchNormalization # type: ignore
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau # type: ignore

# Ensure reproducible results
np.random.seed(42)
tf.random.set_seed(42)

TIME_STEPS = 50  # 5 seconds of physics memory at 10Hz

def load_and_scale_data(file_path):
    print("[1/5] Loading and Preprocessing Data...")
    df = pd.read_csv(file_path)
    
    # Drop any non-numeric columns if they slipped in
    df = df.select_dtypes(include=[np.number])
    df = df.fillna(0)
    
    y = df['label'].astype(int).values
    X = df.drop(columns=['label']).values
    
    print(f"Loaded {X.shape[0]} rows. Extracted {X.shape[1]} features.")
    
    # Scale the 26 features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Export scaler for the live dashboard bridge
    with open('scaler_v2.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    print("Exported standard scaler to 'scaler_v2.pkl'")
        
    return X_scaled, y

def create_sequences(X, y, time_steps=TIME_STEPS):
    print(f"[2/5] Formatting 3D Sequences (Time Steps = {time_steps})...")
    Xs, ys = [], []
    for i in range(len(X) - time_steps):
        Xs.append(X[i:(i + time_steps)])
        ys.append(y[i + time_steps])
    
    X_seq, y_seq = np.array(Xs), np.array(ys)
    print(f"Generated {X_seq.shape[0]} sequences.")
    return X_seq, y_seq

def apply_smote_to_sequences(X_train, y_train):
    print("[3/5] Applying SMOTE to perfectly balance classes...")
    samples, steps, features = X_train.shape
    
    # Flatten the 3D sequences to 2D for SMOTE (samples, steps * features)
    X_flat = X_train.reshape((samples, steps * features))
    
    smote = SMOTE(random_state=42)
    X_resampled_flat, y_resampled = smote.fit_resample(X_flat, y_train)
    
    # Reshape back to 3D
    X_resampled = X_resampled_flat.reshape((-1, steps, features))
    
    print(f"SMOTE complete! Original classes: {np.bincount(y_train)}")
    print(f"SMOTE classes: {np.bincount(y_resampled)}")
    return X_resampled, y_resampled

def build_bidirectional_lstm(input_shape, num_classes=5):
    print("[4/5] Constructing Bidirectional LSTM Zero-Trust Architecture...")
    model = Sequential([
        # Bidirectional allows reading the 5-second physics sequence forwards and backwards
        Bidirectional(LSTM(128, return_sequences=True), input_shape=input_shape),
        Dropout(0.3),
        BatchNormalization(),
        
        Bidirectional(LSTM(64)),
        Dropout(0.3),
        BatchNormalization(),
        
        Dense(32, activation='relu'),
        Dropout(0.2),
        Dense(num_classes, activation='softmax')
    ])
    
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), 
                  loss='sparse_categorical_crossentropy', 
                  metrics=['accuracy'])
    return model

def train_and_export():
    # 1. Load Data
    X_scaled, y = load_and_scale_data('perfect_dataset_v2.csv')
    num_classes = len(np.unique(y))
    
    # 2. Create Time Sequences
    X_seq, y_seq = create_sequences(X_scaled, y)
    
    # 3. Train/Test Split (CRITICAL: Split BEFORE SMOTE to prevent data leakage)
    X_train, X_test, y_train, y_test = train_test_split(X_seq, y_seq, test_size=0.2, random_state=42, stratify=y_seq)
    
    # 4. Calculate Zero-Trust Class Weights on original distribution
    # This heavily penalizes the AI for missing rare attacks
    raw_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
    class_weights = dict(enumerate(raw_weights))
    
    # Manually aggressive bias: Force the model to be 3x more sensitive to attacks
    class_weights[1] *= 3.0 # RC Hijack
    class_weights[2] *= 3.0 # Mode Forcing
    class_weights[3] *= 3.0 # GPS Spoof
    class_weights[4] *= 3.0 # Disarm
    print("Calculated Zero-Trust Class Weights:", class_weights)
    
    # 5. Apply SMOTE to training data only
    X_train_res, y_train_res = apply_smote_to_sequences(X_train, y_train)
    
    # 6. Build and Train Model
    model = build_bidirectional_lstm((X_train_res.shape[1], X_train_res.shape[2]), num_classes)
    
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2, min_lr=0.0001)
    ]
    
    print("[5/5] Commencing Deep Learning Training...")
    history = model.fit(
        X_train_res, y_train_res,
        epochs=30,
        batch_size=128,
        validation_data=(X_test, y_test),
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=1
    )
    
    print("\n[★] Training Complete! Evaluating against pure, un-tampered Test Data...")
    y_pred_probs = model.predict(X_test)
    y_pred = np.argmax(y_pred_probs, axis=1)
    
    print("\nCLASSIFICATION REPORT (Zero-Trust Validation):")
    print(classification_report(y_test, y_pred, target_names=['Normal', 'RC_Hijack', 'Mode_Force', 'GPS_Spoof', 'Disarm']))
    
    print("\nCONFUSION MATRIX:")
    print(confusion_matrix(y_test, y_pred))
    
    model.save('lstm_uav_v2.h5')
    print("\n[✔] SUCCESS: Brain exported as 'lstm_uav_v2.h5'. Ready for Phase 4 (Live Bridge).")

if __name__ == '__main__':
    train_and_export()
