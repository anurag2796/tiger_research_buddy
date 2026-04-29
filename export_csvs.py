import json
import csv
from pathlib import Path

def export_to_csv():
    print("Loading tiger_brain.json...")
    with open('data/tiger_brain.json', 'r') as f:
        data = json.load(f)
        
    nodes = data.get('nodes', [])
    links = data.get('links', [])
    
    # Filter out missing type nodes
    nodes = [n for n in nodes if n.get('type')]
    valid_ids = {n['id'] for n in nodes}
    
    links = [l for l in links if l.get('source') in valid_ids and l.get('target') in valid_ids]
    
    print(f"Exporting {len(nodes)} nodes...")
    with open('data/nodes.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'type', 'label'])
        for n in nodes:
            label = n.get('label') or n.get('name') or n.get('id', '')
            # Clean newlines from labels
            label = str(label).replace('\n', ' ').replace('\r', '')
            writer.writerow([n.get('id'), n.get('type', 'unknown'), label])
            
    print(f"Exporting {len(links)} edges...")
    with open('data/edges.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['source', 'target', 'type'])
        for l in links:
            writer.writerow([l.get('source'), l.get('target'), l.get('type', 'UNKNOWN')])
            
    print("Done! Files saved as data/nodes.csv and data/edges.csv")

if __name__ == "__main__":
    export_to_csv()
