import os
os.environ["TORCH_DEVICE"] = "cpu"
from surya.layout import LayoutPredictor
try:
    predictor = LayoutPredictor()
    print("SUCCESS")
except Exception as e:
    print("FAILED:", e)
