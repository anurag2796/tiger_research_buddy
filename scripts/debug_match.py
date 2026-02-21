from src.crawlers.paper_downloader_v3 import PaperDownloader

def debug_mismatch():
    d = PaperDownloader()
    
    # Fail Case from verified data
    # ❌ benjamin_social-media_based_personas_challenge_hybrid_prediction_of_c.json Mismatch! Faculty: Ashique KhudaBukhsh, Authors: ['Benjamin White', 'Anastasia Shimorina']
    
    fac = "Ashique KhudaBukhsh"
    authors = ['Benjamin White', 'Anastasia Shimorina']
    match = d._is_author_match(fac, authors)
    print(f"'{fac}' vs {authors} => {match}")
    
    if match:
        print("❌ LOGIC ERROR: Should be False!")
    else:
        print("✅ LOGIC CORRECT: Returns False.")
        

if __name__ == "__main__":
    debug_mismatch()
