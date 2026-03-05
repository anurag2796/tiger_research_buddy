"""VLM Target Prompting — isolated visual element extraction.

Crops a bounding-box region (Table or Figure) from a page image and passes
*only* that image to a Vision-Language Model with a strict extraction prompt.
Results come back as clean Markdown, ready to inject into TigerCard 2.0.

Architecture note:
    The VLM inference layer is intentionally separated from lay-out parsing so
    that the heavy model call can be re-routed to a remote GPU server later.
    Switch ``backend="remote"`` and supply an ``endpoint_url`` to activate the
    remote path (stub only — implement when Ubuntu box is ready).
"""

import io
import base64
import logging
from typing import Optional, Protocol, runtime_checkable

from PIL import Image

logger = logging.getLogger("VLMTargetExtractor")

# ── Target prompts per element type ───────────────────────────────────────────

TARGET_PROMPTS = {
    "Table": (
        "Extract only the raw Markdown table from this image. "
        "Do not include introductory text, explanations, or surrounding "
        "document context. Return purely the Markdown representation."
    ),
    "Figure": (
        "Extract only the raw Markdown data from this image. "
        "Do not include introductory text, explanations, or surrounding "
        "document context. Return purely the Markdown representation."
    ),
}

DEFAULT_PROMPT = TARGET_PROMPTS["Figure"]


# ── Backend protocol (for future remote routing) ─────────────────────────────

@runtime_checkable
class VLMBackend(Protocol):
    """Interface that any VLM backend must satisfy."""

    def extract(self, image: Image.Image, prompt: str) -> str:
        """Send an image + prompt and return extracted Markdown text."""
        ...


# ── Local Ollama backend ─────────────────────────────────────────────────────

class OllamaVLMBackend:
    """Runs VLM inference locally via Ollama's multimodal chat API.

    Requires a vision-capable model (e.g. ``llava``, ``bakllava``,
    ``minicpm-v``, ``llava-llama3``).  The ``images`` parameter of
    ``ollama.chat`` accepts base64-encoded image strings.
    """

    def __init__(self, model: str = "llava"):
        self.model = model

    def extract(self, image: Image.Image, prompt: str) -> str:
        try:
            import ollama
        except ImportError:
            logger.error("ollama package not installed — cannot run local VLM")
            return ""

        # Encode the PIL image → base64 PNG
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [b64_img],
                    }
                ],
            )
            return response["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Ollama VLM call failed: {e}")
            return ""


# ── Remote backend stub ──────────────────────────────────────────────────────

class RemoteVLMBackend:
    """Placeholder for a remote GPU server.

    When the Ubuntu inference box is ready, implement ``extract()`` to POST
    the image to ``self.endpoint_url`` and return the Markdown response.
    """

    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url

    def extract(self, image: Image.Image, prompt: str) -> str:
        raise NotImplementedError(
            f"Remote VLM backend not yet implemented. "
            f"Target endpoint: {self.endpoint_url}"
        )


# ── Public interface ─────────────────────────────────────────────────────────

class VLMTargetExtractor:
    """Orchestrates targeted VLM extraction on cropped visual elements.

    Parameters
    ----------
    backend : str
        ``"local"`` → Ollama  |  ``"remote"`` → HTTP to GPU server.
    model : str
        Vision model name for the local backend (ignored for remote).
    endpoint_url : str | None
        Required when ``backend="remote"``.
    """

    def __init__(
        self,
        backend: str = "local",
        model: str = "llava",
        endpoint_url: Optional[str] = None,
    ):
        if backend == "remote":
            if not endpoint_url:
                raise ValueError("endpoint_url required for remote backend")
            self._backend: VLMBackend = RemoteVLMBackend(endpoint_url)
        else:
            self._backend = OllamaVLMBackend(model=model)

    def extract(self, image: Image.Image, element_type: str = "Figure") -> str:
        """Extract Markdown from a cropped visual element image.

        Parameters
        ----------
        image : PIL.Image.Image
            The cropped bounding-box image of a table, figure, or chart.
        element_type : str
            ``"Table"`` or ``"Figure"`` — selects the target prompt variant.

        Returns
        -------
        str
            Raw Markdown extracted by the VLM, or empty string on failure.
        """
        prompt = TARGET_PROMPTS.get(element_type, DEFAULT_PROMPT)
        return self._backend.extract(image, prompt)
