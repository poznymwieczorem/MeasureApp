import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import io
from django.core.files.base import ContentFile

def process_dta_file(measurement_instance):
    """
    Process the uploaded .dta file, extract peaks, and update the Measurement instance.
    """

    raw_file = measurement_instance.raw_file
    if not raw_file:
        return # No file to process
    raw_file.open(mode="rb")
    content = raw_file.read().decode('utf-8', errors='ignore')
    raw_file.close()

    # Find the section with data
    lines = content.splitlines()
    data_start = -1
    for i, line in enumerate(lines):
        if "CURVE" in line:
            for j in range(i + 1, min(i + 10, len(lines))):
                if "Pt" in lines[j] and "Vf" in lines[j]:
                    data_start = j
                    break
            if data_start != -1: break
    
    if data_start == -1:
        print("Data section not found in the .dta file.")
        return

    try:
        df = pd.read_csv(
            io.StringIO("\n".join(lines[data_start:])),
            sep=None,
            engine='python',
            on_bad_lines='skip'
        )

        df.columns = [c.strip() for c in df.columns]

        for col in ['Vf', 'Im']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=['Vf', 'Im'])

        if df.empty:
            print("No valid data found after processing the .dta file.")
            return

        # Save processed CSV to the Measurement instance
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = ContentFile(csv_buffer.getvalue().encode('utf-8'))

        csv_name = f"{raw_file.name.split('/')[-1].replace('.DTA', '')}.csv"
        measurement_instance.csv_file.save(csv_name, csv_content, save=False)

        if 'Im' in df.columns and 'Vf' in df.columns:

            peaks, _ = find_peaks(df['Im'], distance=20) # For TEST purposes, we set distance=1 to find all peaks. In production, this should be adjusted based on expected data characteristics.

            if len(peaks) > 0:
                
                highest_idx = peaks[np.argmax(df['Im'].iloc[peaks])]
                measurement_instance.peak_potelntial = df['Vf'].iloc[highest_idx]
                measurement_instance.peak_current = df['Im'].iloc[highest_idx]
            else:
                
                max_idx = df['Im'].idxmax()
                measurement_instance.peak_potelntial = df['Vf'].loc[max_idx]
                measurement_instance.peak_current = df['Im'].loc[max_idx]
    except Exception as e:
        print(f"Error processing file: {e}")