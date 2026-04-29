import pandas as pd
import argparse

def combine_datasets(normal_file, attack_file, output_file):
    print(f"Loading normal data from {normal_file}...")
    df_normal = pd.read_csv(normal_file)
    print(f"Normal data shape: {df_normal.shape}")
    
    print(f"Loading attack data from {attack_file}...")
    df_attack = pd.read_csv(attack_file)
    print(f"Attack data shape: {df_attack.shape}")
    
    print("Combining datasets...")
    # Concatenate the two dataframes
    df_combined = pd.concat([df_normal, df_attack], ignore_index=True)
    
    # Sort by timestamp to make sure time-series order is maintained
    df_combined = df_combined.sort_values(by='timestamp').reset_index(drop=True)
    
    print(f"Saving combined dataset to {output_file}...")
    df_combined.to_csv(output_file, index=False)
    
    print(f"Done! Final dataset shape: {df_combined.shape}")
    print("\nLabel distribution:")
    print(df_combined['label'].value_counts())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Combine MAVLink Telemetry CSVs')
    parser.add_argument('--normal', default='normal_flight_data.csv', help='Normal data CSV.')
    parser.add_argument('--attack', default='attack_flight_data.csv', help='Attack data CSV.')
    parser.add_argument('--out', default='combined_dataset.csv', help='Combined output CSV.')
    args = parser.parse_args()
    
    combine_datasets(args.normal, args.attack, args.out)
