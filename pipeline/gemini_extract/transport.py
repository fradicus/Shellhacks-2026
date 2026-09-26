"""The only network boundary. No uploads, tools, arbitrary endpoints, or implicit live mode."""

from __future__ import annotations

import re

import httpx
from google import genai
from google.genai import errors, types

from .prompt import SYSTEM_INSTRUCTION, document_prompt, response_schema
from .sources import Page, verify_for_transport

MODEL_RE = re.compile(r"(?:models/)?gemini-[A-Za-z0-9._-]{1,100}")


class TransportFailure(Exception):
    def __init__(self, reason: str, transient: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.transient = transient


class GeminiTransport:
    def __init__(self, api_key: str, model: str):
        if not api_key or not MODEL_RE.fullmatch(model):
            raise TransportFailure("gemini_configuration_invalid")
        self.model = model
        # SDK defaults allow five attempts. One means the runner owns the complete retry budget.
        self.client = genai.Client(
            api_key=api_key,
            vertexai=False,
            http_options=types.HttpOptions(
                base_url="https://generativelanguage.googleapis.com",
                timeout=60_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def generate(self, page: Page) -> str:
        verify_for_transport(page)
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=document_prompt(page),
                config=types.GenerateContentConfig(
                    temperature=0,
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_json_schema=response_schema(),
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            if not response.text:
                raise TransportFailure("gemini_empty_or_blocked_response")
            return response.text
        except errors.APIError as exc:
            # Never persist str(exc), request headers, API key, HTTP body or SDK repr.
            transient = exc.code in (408, 429, 500, 502, 503, 504)
            raise TransportFailure("gemini_transient_error" if transient else "gemini_request_rejected", transient) from None
        except (httpx.TimeoutException, httpx.TransportError):
            raise TransportFailure("gemini_transport_error", transient=True) from None

    def close(self) -> None:
        self.client.close()
