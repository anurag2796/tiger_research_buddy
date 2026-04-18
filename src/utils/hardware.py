"""Hardware detection and platform-aware configuration for TigerResearchBuddy.

This is the single source of truth for all hardware-aware decisions.
Never hardcode device flags (mps/cuda/cpu), concurrency limits, or
context windows elsewhere. Always read from ``HW_PROFILE``.

Supported targets:
  - macOS / Apple Silicon (M-series, MPS)
  - Linux  / Nvidia Jetson Orin (CUDA, ARM64)
  - Linux  / CPU-only fallback
"""

from __future__ import annotations

import os
import sys
import platform
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Platform type alias
# ---------------------------------------------------------------------------
Platform = Literal["macos_apple_silicon", "macos_x86", "linux_cuda", "linux_cpu"]


# ---------------------------------------------------------------------------
# HardwareProfile — immutable snapshot of detected capabilities
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HardwareProfile:
    """Immutable hardware profile built once at module import time."""

    # Identity
    platform: Platform
    arch: str                    # e.g. "arm64", "x86_64"
    is_macos: bool
    is_linux: bool
    is_apple_silicon: bool
    has_cuda: bool
    has_mps: bool

    # PyTorch device string — safe to pass to torch.device() or SentenceTransformers
    torch_device: str            # "mps" | "cuda" | "cpu"
    embedding_device: str        # same but may differ if MPS has meta-tensor issues

    # LLM resource limits
    context_window: int          # Ollama num_ctx
    chat_concurrency: int        # asyncio.Semaphore value for Ollama async calls
    distiller_concurrency: int   # asyncio.Semaphore for DeepDistiller batch

    # Memory module
    memory_window: int           # Sliding-window deque maxlen (in individual messages)

    # PDF pipeline
    pdf_engine: str              # "apple_fast" | "marker" | "pymupdf"


# ---------------------------------------------------------------------------
# Internal detection helpers
# ---------------------------------------------------------------------------

def _detect_torch_capabilities() -> tuple[bool, bool]:
    """Check PyTorch backend availability. Returns (has_cuda, has_mps)."""
    try:
        import torch
        has_cuda = torch.cuda.is_available()
        has_mps = (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
            and torch.backends.mps.is_built()
        )
        return has_cuda, has_mps
    except ImportError:
        return False, False


def _get_torch_device(has_cuda: bool, has_mps: bool) -> str:
    """Return the preferred PyTorch device string, in priority order."""
    if has_mps:
        return "mps"
    if has_cuda:
        return "cuda"
    return "cpu"


def _get_embedding_device(has_cuda: bool, has_mps: bool) -> str:
    """Return device string for SentenceTransformers.

    MPS has a known bug with the ``nomic-embed-text-v1.5`` model where
    SentenceTransformer initialisation triggers a ``NotImplementedError``
    (meta-tensor copy).  We detect this at build-time and fall back to CPU
    while keeping the ``torch_device`` as "mps" for other uses.

    The per-device override ``EMBEDDING_DEVICE`` env var always wins.
    """
    env_override = os.getenv("EMBEDDING_DEVICE", "").strip().lower()
    if env_override in ("cpu", "cuda", "mps"):
        return env_override

    # MPS + nomic model = meta-tensor bug; use CPU for embeddings on Apple Silicon
    if has_mps:
        return "cpu"
    if has_cuda:
        return "cuda"
    return "cpu"


def _get_pdf_engine(is_macos: bool) -> str:
    """Select the PDF extraction engine based on platform.

    Override with ``PDF_ENGINE`` env var (e.g. ``PDF_ENGINE=pymupdf``).
    """
    env_override = os.getenv("PDF_ENGINE", "").strip().lower()
    if env_override in ("apple_fast", "marker", "pymupdf"):
        return env_override

    if is_macos:
        return "apple_fast"
    # On Linux/Jetson: prefer pymupdf (pure-Python, no extra deps).
    # marker requires PyTorch inference — choose only if explicitly set.
    return "pymupdf"


def _detect_platform(is_macos: bool, is_apple_silicon: bool, has_cuda: bool) -> Platform:
    if is_macos and is_apple_silicon:
        return "macos_apple_silicon"
    if is_macos:
        return "macos_x86"
    if has_cuda:
        return "linux_cuda"
    return "linux_cpu"


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def build_hardware_profile() -> HardwareProfile:
    """Build a ``HardwareProfile`` by probing the current environment.

    Resource limits are sourced from environment variables so the same
    codebase runs on both the M4 Max and the Jetson Orin without edits.

    Environment variable overrides
    --------------------------------
    OLLAMA_CHAT_CONCURRENCY   int  (default: 2 macOS / 1 Linux)
    DISTILLER_CONCURRENCY     int  (default: 3 macOS / 1 Linux)
    LLM_CONTEXT_WINDOW        int  (default: 16384 macOS / 8192 Linux)
    MEMORY_WINDOW             int  (default: 20 macOS / 6 Linux)
    PDF_ENGINE                str  (default: apple_fast macOS / pymupdf Linux)
    EMBEDDING_DEVICE          str  (default: cpu — see docstring)
    """
    is_macos = sys.platform == "darwin"
    is_linux = sys.platform.startswith("linux")
    arch = platform.machine().lower()                # "arm64", "x86_64", "aarch64"
    is_apple_silicon = is_macos and arch in ("arm64", "aarch64")

    has_cuda, has_mps = _detect_torch_capabilities()

    torch_device = _get_torch_device(has_cuda, has_mps)
    embedding_device = _get_embedding_device(has_cuda, has_mps)
    pdf_engine = _get_pdf_engine(is_macos)
    detected_platform = _detect_platform(is_macos, is_apple_silicon, has_cuda)

    # ---- Resource limits (env var > platform default) ----
    _mac = is_macos  # shorthand
    chat_concurrency = int(os.getenv("OLLAMA_CHAT_CONCURRENCY", "2" if _mac else "1"))
    distiller_concurrency = int(os.getenv("DISTILLER_CONCURRENCY", "3" if _mac else "1"))
    context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "16384" if _mac else "8192"))
    memory_window = int(os.getenv("MEMORY_WINDOW", "20" if _mac else "6"))

    return HardwareProfile(
        platform=detected_platform,
        arch=arch,
        is_macos=is_macos,
        is_linux=is_linux,
        is_apple_silicon=is_apple_silicon,
        has_cuda=has_cuda,
        has_mps=has_mps,
        torch_device=torch_device,
        embedding_device=embedding_device,
        context_window=context_window,
        chat_concurrency=chat_concurrency,
        distiller_concurrency=distiller_concurrency,
        memory_window=memory_window,
        pdf_engine=pdf_engine,
    )


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly:
#   from src.utils.hardware import HW_PROFILE
# ---------------------------------------------------------------------------

HW_PROFILE: HardwareProfile = build_hardware_profile()


# ---------------------------------------------------------------------------
# Convenience re-exports
# ---------------------------------------------------------------------------

def get_torch_device() -> str:
    """Return the best available PyTorch device string."""
    return HW_PROFILE.torch_device


def get_embedding_device() -> str:
    """Return the device to pass to SentenceTransformers."""
    return HW_PROFILE.embedding_device


def detect_platform() -> Platform:
    """Return the detected platform identifier string."""
    return HW_PROFILE.platform


if __name__ == "__main__":
    # Quick CLI check: python -m src.utils.hardware
    from rich.console import Console
    from rich.table import Table

    c = Console()
    t = Table(title="🐅 TigerResearchBuddy — Hardware Profile", show_lines=True)
    t.add_column("Property", style="cyan")
    t.add_column("Value", style="green")

    for f_name, f_val in HW_PROFILE.__dataclass_fields__.items():
        t.add_row(f_name, str(getattr(HW_PROFILE, f_name)))

    c.print(t)
