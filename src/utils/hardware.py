"""Hardware detection and platform-aware configuration for TigerResearchBuddy.
This is the single source of truth for all hardware-aware decisions.
Never hardcode device flags (mps/cuda), concurrency limits, or
context windows elsewhere. Always read from ``HW_PROFILE``.
"""

from __future__ import annotations

import os
import sys
import platform
import ctypes
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Platform type alias
# ---------------------------------------------------------------------------
Platform = Literal["macos_apple_silicon", "macos_x86", "linux_cuda", "linux_cpu"]


# ---------------------------------------------------------------------------
# Library Path Automation (Jetson/CUDA Fixes)
# ---------------------------------------------------------------------------

def _setup_library_paths():
    """Project-local fix for Jetson/CUDA library dependencies."""
    project_root = Path(__file__).parent.parent.parent
    local_libs = project_root / "libs"
    
    if local_libs.exists():
        libs_path = str(local_libs.absolute())
        
        # 1. Update LD_LIBRARY_PATH for child processes (like subprocesses)
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if libs_path not in current_ld:
            os.environ["LD_LIBRARY_PATH"] = f"{libs_path}:{current_ld}"
        
        # 2. Pre-load specific libraries that torch needs but may not find on Jetson
        try:
            # Load cuSPARSELt which is often missing from base JetPack 6.2
            cusparse_lt = local_libs / "libcusparseLt.so.0"
            if cusparse_lt.exists():
                ctypes.CDLL(str(cusparse_lt.absolute()), mode=ctypes.RTLD_GLOBAL)
        except Exception as e:
            # We don't want to crash at import time, but we should log it
            print(f"DEBUG [hardware.py]: Could not pre-load libcusparseLt: {e}")

# Run setup at module import time
_setup_library_paths()


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
# -------------------------------------------------------------------------

def _detect_torch_capabilities() -> tuple[bool, bool]:
    """Check PyTorch backend availability. Returns (has_cuda, has_mps)."""
    try:
        import torch
        has_cuda = False
        has_mps = False
        if torch.cuda.is_available():
            try:
                # Test if we can actually use CUDA (e.g., query device name)
                # This catches the "driver too old" error that is_available() misses.
                _ = torch.cuda.get_device_name(0)
                has_cuda = True
            except Exception as e:
                print(f"CUDA is available but unusable: {e}")
                has_cuda = False
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() and torch.backends.mps.is_built():
            has_mps = True
        return has_cuda, has_mps
    except Exception:
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

    The per-device override ``EMBEDDING_DEVICE`` env var always wins —
    *unless* it requests "cuda" when CUDA is not actually available, in
    which case we override back to "cpu" and log a warning.
    """
    env_override = os.getenv("EMBEDDING_DEVICE", "").strip().lower()
    if env_override in ("cpu", "cuda", "mps"):
        resolved = env_override
    elif has_mps:
        # MPS + nomic model = meta-tensor bug; use CPU for embeddings on Apple Silicon
        resolved = "cpu"
    elif has_cuda:
        resolved = "cuda"
    else:
        resolved = "cpu"

    # Guard: never report cuda when CUDA is actually unavailable
    if resolved == "cuda" and not has_cuda:
        print(
            "WARNING [hardware.py]: EMBEDDING_DEVICE=cuda in .env but CUDA is not "
            "available (has_cuda=False). Overriding to 'cpu'. "
            "Install a CUDA-compatible PyTorch wheel to enable GPU embeddings."
        )
        resolved = "cpu"

    return resolved


def _get_pdf_engine(is_macos: bool) -> str:
    """Select the PDF extraction engine based on platform.
    Override with ``PDF_ENGINE`` env var (e.g. ``PDF_ENGINE=pymupdf``).
    """
    env_override = os.getenv("PDF_ENGINE", "").strip().lower()
    if env_override in ("apple_fast", "marker", "pymupdf"):
        return env_override

    if is_macos:
        return "apple_fast"
    # On Linux/Jetson: prefer pymupfor (pure-Python, no extra deps).
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
    LLM_CONTEXT_WINDOW        int  (default: 1638_4 macOS / 8192 Linux)
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
    chat_con_limit = int(os.getenv("OLLAMA_CHAT_CONCURRENCY", "2" if _mac else "1"))
    dist_con_limit = int(os.getenv("DISTILLER_CONCURRENCY", "3" if _mac else "1"))
    ctx_window = int(os.getenv("LLM_CONTEXT_WINDOW", "16384" if _mac else "8192"))
    mem_window = int(os.getenv("MEMORY_WINDOW", "20" if _mac else "6"))

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
        context_window=ctx_window,
        chat_concurrency=chat_con_limit,
        distiller_concurrency=dist_con_limit,
        memory_window=mem_window,
        pdf_engine=pdf_engine,
    )


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly:
#   from src.utils.hardware import HW_PROFILE
# ---------------------------------------------------------------------------
HW_PROFILE: HardwareProfile = build_hardware_profile()


# ---------------------------------------------------------------------------
# Convenience re-exports
# ---------------------------------------------------------------
def get_torch_device() -> str:
    """Return the best available PyTorch device string."""
    return HW_PROFILE.torch_device


def get_embedding_device() -> str:
    """Return the device to pass to SentenceTransformers."""
    return HW_PROFILE.embedding_device


def detect_platform() -> Platform:
    """Return the detected platform identifier string."""
    return HW_PROFILE.platform
