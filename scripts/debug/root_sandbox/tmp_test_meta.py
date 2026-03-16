import traceback

print("Testing Surya LayoutPredictor...")
try:
    from surya.layout import LayoutPredictor
    lp = LayoutPredictor()
    print("Surya: success!")
except Exception as e:
    print(f"Surya failed: {type(e).__name__}: {e}")

print("\nTesting GMFT AutoTableDetector...")
try:
    from gmft.auto import AutoTableDetector, AutoTableFormatter
    detector = AutoTableDetector()
    formatter = AutoTableFormatter()
    print("GMFT: success!")
except Exception as e:
    print(f"GMFT failed: {type(e).__name__}: {e}")
