#!/usr/bin/env python
"""
Manual Gemini smoke test (not run in automated tests).

Usage from backend/:
    python scripts/smoke_gemini.py
"""

import os
import sys
from pathlib import Path

import django

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / '.env')
django.setup()

from llm_gateway import LLMGateway, LLMRequest
from llm_gateway.providers.gemini import GeminiLLMProvider


def main() -> None:
    provider = GeminiLLMProvider()
    gateway = LLMGateway(provider)
    response = gateway.generate(
        LLMRequest(
            prompt='Reply with exactly: GEMINI_OK',
            system_prompt='You are a test assistant. Respond briefly.',
        )
    )
    print(f'Model: {provider.model_name}')
    print(f'Response: {response.content}')


if __name__ == '__main__':
    main()
