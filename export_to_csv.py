#!/usr/bin/env python3
import pandas as pd
import json
import os

# Load the gold tier resources
with open('gold_tier_test/gold/resources.json', 'r') as f:
    data = json.load(f)

# Export each resource type to CSV
for resource_type, resources in data.items():
    if resources:
        # Convert to DataFrame
        df = pd.json_normalize(resources)
        
        # Create output path
        output_path = f'gold_tier_test/gold/{resource_type.lower()}.csv'
        
        # Export to CSV
        df.to_csv(output_path, index=False)
        print(f"Exported {len(resources)} {resource_type} resources to {output_path}")

print("Export complete!") 