#!/usr/bin/env python
"""
Manual Gemini smoke test (not run in automated tests).

Usage from repository root:
    python infrastructure/scripts/smoke_gemini.py
"""

import os
import sys
from pathlib import Path

import django

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / 'backend'
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / '.env')
django.setup()

from gateways.llm import LLMGateway, LLMRequest
from gateways.llm.providers.gemini import GeminiLLMProvider


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
