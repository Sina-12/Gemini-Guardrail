import pandas as pd
import krippendorff
import numpy as np

def calculate_agreement(csv_path):
    """
    Calculates Krippendorff's Alpha for different ordinal scales.
    Ensures Success (1,2) and others (0,1,2) are handled correctly.
    """
    df = pd.read_csv(csv_path)
    
    
    df = df.sort_values(['doc_id', 'annotator'])
    
    categories = ['success', 'brevity', 'accuracy']
    results = {}

    for cat in categories:
        matrix = df.pivot(index='annotator', columns='doc_id', values=cat).to_numpy()
        alpha = krippendorff.alpha(reliability_data=matrix, level_of_measurement='ordinal')
        results[cat] = alpha
        
        print(f"Krippendorff's Alpha for {cat.capitalize()}: {alpha:.3f}")
    
    return results


if __name__ == "__main__":
    import sys
    

    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        calculate_agreement(target_file)
    else:
        print("Please provide a CSV file path")

# To run:
# calculate_agreement('overlap_50_instances.csv')

