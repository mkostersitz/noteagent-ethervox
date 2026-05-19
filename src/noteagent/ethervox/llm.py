"""EtherVox LLM bindings (ctypes wrapper around ethervox_llm_* C API)."""

from __future__ import annotations

import ctypes

from noteagent.ethervox._lib_loader import load_ethervox_lib


class EtherVoxLLM:
    """Python wrapper around the EtherVox LLM backend C API.

    Supports local GGUF models (llama.cpp) and OpenAI-compatible HTTP endpoints.
    """

    def __init__(self, model_path: str = "") -> None:
        lib = load_ethervox_lib()
        self._backend = lib.ethervox_llm_create_llama_backend()
        if model_path:
            lib.ethervox_llm_backend_load_model(self._backend, model_path.encode())
        self._lib = lib
        self._is_openai = False

    @classmethod
    def from_openai(cls, api_key: str = "", base_url: str = "https://api.openai.com/v1") -> "EtherVoxLLM":
        """Return an instance backed by an OpenAI-compatible HTTP endpoint."""
        lib = load_ethervox_lib()
        obj = cls.__new__(cls)
        obj._lib = lib
        obj._backend = lib.ethervox_llm_create_openai_backend(
            api_key.encode(), base_url.encode()
        )
        obj._is_openai = True
        return obj

    def generate(self, prompt: str, language: str = "en") -> str:
        """Generate a text response for *prompt*."""
        result = ctypes.c_char_p()
        self._lib.ethervox_llm_backend_generate(
            self._backend, prompt.encode(), language.encode(), ctypes.byref(result)
        )
        return result.value.decode() if result.value else ""

    def close(self) -> None:
        self._lib.ethervox_llm_backend_destroy(self._backend)
