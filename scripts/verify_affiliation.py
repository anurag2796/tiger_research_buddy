from pathlib import Path
import json
import sys

def verify_affine():
    papers_dir = Path("data/papers")
    if not papers_dir.exists():
        print("Papers dir not found")
        return

    print("Checking recent papers for affiliation flag...")
    
    count = 0
    rit_count = 0
    
    for f in sorted(papers_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:50]:
        try:
            data = json.loads(f.read_text())
            count += 1
            
            has_rit = data.get("has_rit_affiliation", False)
            source = data.get("source", "unknown")
            
            if has_rit:
                rit_count += 1
                print(f"✅ [RIT Verified] {f.name} ({source})")
            else:
                # ArXiv won't have it usually, but let's see
                print(f"Ref: [No Affiliation] {f.name} ({source})")
                
        except Exception:
            pass
            
    print(f"\nStats: {rit_count}/{count} recent papers have explicit RIT affiliation flag.")

if __name__ == "__main__":
    verify_affine()
