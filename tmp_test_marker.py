import traceback
import sys

print("Testing marker-pdf initialization...")
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict

    config = {
        "output_format": "markdown",
        "use_llm": False,
        "disable_image_extraction": True
    }
    artifact_dict = create_model_dict()
    print("Model dictionary created!")
    
    # We shouldn't load an actual PDF unless we have to, but init might crash!
    converter = PdfConverter(
        artifact_dict=artifact_dict,
        config=config
    )
    print("PdfConverter initialized!")
except Exception as e:
    print(f"Marker-pdf failed: {type(e).__name__}: {e}")
    traceback.print_exc()
