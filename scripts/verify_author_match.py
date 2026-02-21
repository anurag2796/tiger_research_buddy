from pathlib import Path
import json
import re

def normalize(name):
    return re.sub(r'[^\w\s]', '', name.lower()).strip()

def is_author_match(faculty_name, paper_authors):
    if not paper_authors: return False
    
    fac_norm = normalize(faculty_name)
    fac_parts = fac_norm.split()
    if not fac_parts: return False
    
    fac_last = fac_parts[-1]
    fac_first_initial = fac_parts[0][0] if len(fac_parts) > 0 else ""
    
    for author in paper_authors:
        auth_norm = normalize(author)
        auth_parts = auth_norm.split()
        if not auth_parts: continue
        
        auth_last = auth_parts[-1]
        
        if fac_last != auth_last: continue
        
        auth_first_initial = auth_parts[0][0] if len(auth_parts) > 0 else ""
        if fac_first_initial == auth_first_initial:
            return True
            
    return False

def check_downloads():
    papers_dir = Path("data/papers")
    if not papers_dir.exists():
        print("Papers dir not found")
        return

    # Check last 50 modified
    recent_files = sorted(papers_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:50]
    
    print(f"Checking {len(recent_files)} most recent downloads for author match...")
    
    match_count = 0
    total = 0
    
    for f in recent_files:
        try:
            data = json.load(f.open())
            total += 1
            
            faculty = data.get("faculty", "Unknown") # PaperDownloader saves this
            authors = data.get("authors", [])
            title = data.get("title", "")
            
            if faculty == "Unknown":
                print(f"⚠️ {f.name}: No faculty recorded in metadata. Old file?")
                continue
                
            if is_author_match(faculty, authors):
                match_count += 1
                # print(f"✅ {f.name} ({faculty}) matched in {authors[:3]}...")
            else:
                print(f"❌ {f.name} Mismatch! Faculty: {faculty}, Authors: {authors}")
                
        except Exception as e:
            print(f"Error reading {f.name}: {e}")
            
    print(f"\nSummary: {match_count}/{total} papers matched their target faculty.")

if __name__ == "__main__":
    check_downloads()
