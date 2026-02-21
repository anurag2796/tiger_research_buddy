import sys
from pathlib import Path
sys.path.append(".")
from src.crawlers.vision_crawler import VisionCrawler

def test_ocr_fix():
    pdf_path = Path("data/pdfs/georgios_detection_of_developmental_language_disorder_in_cypriot_gree.pdf")
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return

    print(f"Testing OCR fix on {pdf_path.name}...")
    crawler = VisionCrawler(engine="apple_fast")
    
    # excessive logging?
    try:
        result = crawler.convert(str(pdf_path), force_reprocess=True)
        content = result.get("content", "")
        
        print(f"\n--- Content Preview (First 500 chars) ---")
        print(content[:500])
        print("-----------------------------------------")
        
        if "[OCR Required but Surya not available]" in content:
            print("❌ FAILURE: Placeholder text still present!")
        elif len(content.strip()) < 50:
            print("⚠️ WARNING: content is very short/empty. OCR might have failed silently or returned empty string.")
        else:
            print("✅ SUCCESS: Content extracted without placeholder error.")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_ocr_fix()
