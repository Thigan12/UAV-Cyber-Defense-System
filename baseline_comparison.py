import pandas as pd
import numpy as np
import pickle
import time
import os
import warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
tf.get_logger().setLevel('ERROR')

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

print("Loading dataset...")
df = pd.read_csv('perfect_dataset_v2.csv')
feature_cols = [c for c in df.columns if c not in ['label','class_name']]
X = df[feature_cols].values
y = df['label'].values

# Split data
X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)
X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.176, random_state=42, stratify=y_temp)

# Scale data
with open('scaler_v2.pkl', 'rb') as f:
    scaler = pickle.load(f)

X_train_sc = scaler.transform(X_train)
X_val_sc = scaler.transform(X_val)
X_test_sc = scaler.transform(X_test)

# Sequence generation for Deep Learning models
SEQ_LEN = 50
def make_sequences(X, y, seq_len=50):
    Xs, ys = [], []
    for i in range(len(X) - seq_len):
        Xs.append(X[i:i+seq_len])
        ys.append(y[i+seq_len-1])
    return np.array(Xs), np.array(ys)

print("Building sequences...")
X_train_seq, y_train_seq = make_sequences(X_train_sc, y_train)
X_test_seq, y_test_seq = make_sequences(X_test_sc, y_test)

# Since traditional ML models (LR, RF) don't naturally handle 3D sequence data natively, 
# we flatten the sequences for them, or just use the raw features. We will flatten the 50x26 sequences.
X_train_flat = X_train_seq.reshape(X_train_seq.shape[0], -1)
X_test_flat = X_test_seq.reshape(X_test_seq.shape[0], -1)

# To speed up LR and RF training, we can use a subset of training data if needed, but we have ~28k, which is fine.
# Results dictionary
results = []

def evaluate_model(name, y_true, y_pred, inf_time_ms):
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='macro', zero_division=0)
    results.append({
        'Model': name,
        'Accuracy': acc,
        'Macro Precision': prec,
        'Macro Recall': rec,
        'Macro F1': f1,
        'Inference Time (ms)': inf_time_ms
    })
    print(f"[{name}] Acc: {acc:.4f} | F1: {f1:.4f} | Time: {inf_time_ms:.2f}ms")

# 1. Logistic Regression
print("\nTraining Logistic Regression...")
lr = LogisticRegression(max_iter=500, n_jobs=-1, random_state=42)
lr.fit(X_train_flat, y_train_seq)
t0 = time.perf_counter()
_ = lr.predict(X_test_flat[:500]) # 500 samples
t1 = time.perf_counter()
inf_ms = ((t1-t0)/500) * 1000
y_pred = lr.predict(X_test_flat)
evaluate_model("Logistic Regression", y_test_seq, y_pred, inf_ms)

# 2. Random Forest
print("\nTraining Random Forest...")
rf = RandomForestClassifier(n_estimators=100, max_depth=15, n_jobs=-1, random_state=42)
rf.fit(X_train_flat, y_train_seq)
t0 = time.perf_counter()
_ = rf.predict(X_test_flat[:500])
t1 = time.perf_counter()
inf_ms = ((t1-t0)/500) * 1000
y_pred = rf.predict(X_test_flat)
evaluate_model("Random Forest", y_test_seq, y_pred, inf_ms)

# 3. Standard LSTM
print("\nTraining Standard LSTM (fast training 5 epochs)...")
lstm = tf.keras.Sequential([
    tf.keras.layers.LSTM(64, input_shape=(50, 26)),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(5, activation='softmax')
])
lstm.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
lstm.fit(X_train_seq, y_train_seq, epochs=5, batch_size=128, verbose=0)
# warmup
_ = lstm.predict(X_test_seq[:5], verbose=0)
# timing
times = []
for i in range(500):
    inp = X_test_seq[i:i+1]
    t0 = time.perf_counter()
    lstm.predict(inp, verbose=0)
    t1 = time.perf_counter()
    times.append((t1-t0)*1000)
inf_ms = np.mean(times)
y_pred = np.argmax(lstm.predict(X_test_seq, verbose=0), axis=1)
evaluate_model("Standard LSTM", y_test_seq, y_pred, inf_ms)

# 4. GRU
print("\nTraining GRU (fast training 5 epochs)...")
gru = tf.keras.Sequential([
    tf.keras.layers.GRU(64, input_shape=(50, 26)),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(5, activation='softmax')
])
gru.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
gru.fit(X_train_seq, y_train_seq, epochs=5, batch_size=128, verbose=0)
# warmup
_ = gru.predict(X_test_seq[:5], verbose=0)
# timing
times = []
for i in range(500):
    inp = X_test_seq[i:i+1]
    t0 = time.perf_counter()
    gru.predict(inp, verbose=0)
    t1 = time.perf_counter()
    times.append((t1-t0)*1000)
inf_ms = np.mean(times)
y_pred = np.argmax(gru.predict(X_test_seq, verbose=0), axis=1)
evaluate_model("GRU", y_test_seq, y_pred, inf_ms)

# 5. Bring in your existing BiLSTM stats for comparison
print("\n[Proposed BiLSTM] Getting stats...")
bilstm = tf.keras.models.load_model('lstm_uav_v2.h5')
# warmup
_ = bilstm.predict(X_test_seq[:5], verbose=0)
# timing
times = []
for i in range(500):
    inp = X_test_seq[i:i+1]
    t0 = time.perf_counter()
    bilstm.predict(inp, verbose=0)
    t1 = time.perf_counter()
    times.append((t1-t0)*1000)
inf_ms = np.mean(times)
y_pred = np.argmax(bilstm.predict(X_test_seq, verbose=0), axis=1)
evaluate_model("Proposed BiLSTM", y_test_seq, y_pred, inf_ms)

print("\n\n=== FINAL BASELINE COMPARISON TABLE ===")
print("| Model | Accuracy | Macro Precision | Macro Recall | Macro F1-score | Mean Inference Time |")
print("|---|---|---|---|---|---|")
for r in results:
    print(f"| {r['Model']} | {r['Accuracy']:.4f} | {r['Macro Precision']:.4f} | {r['Macro Recall']:.4f} | {r['Macro F1']:.4f} | {r['Inference Time (ms)']:.2f} ms |")
