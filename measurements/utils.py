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
    data_start = 0
    for i, line in enumerate(lines):
        if "CURVER" in line and "TABLE" in line:
            data_start = i + 3
            break
    
    try:
        df = pd.read_csv(io.StringIO("\n".join(lines[data_start:])), sep='\t')

        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = ContentFile(csv_buffer.getvalue().encode('utf-8'))

        csv_name = f"{raw_file.name.split('/')[-1].replace('.DTA', '')}.csv"
        measurement_instance.csv_file.save(csv_name, csv_content, save=False)

        if 'Im' in df.columns and 'Vf' in df.columns:

            peaks, _ = find_peaks(df['Im'], distance=20)
            if len(peaks) > 0:
                highest_peak_idx = peaks[np.argmax(df['Im'].iloc[peaks])]
                measurement_instance.peak_potential = df['Vf'].iloc[highest_peak_idx]
                measurement_instance.peak_current = df['Im'].iloc[highest_peak_idx]

    except Exception as e:
        print(f"Error processing file: {e}")