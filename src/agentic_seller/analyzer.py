from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

from .config import Settings
from .models import ListingPlan, ProductInput


class ListingAnalyzer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.usage_totals = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
        }
        self.usage_available = False
        # In a real local copilot-integrated environment, we might use a local LLM endpoint
        # or a specific environment-provided token. For this request, I will simplify 
        # the analyzer to work with a generic local endpoint (like LM Studio or Ollama)
        # which is the common way to use 'free' models in a dev environment.
        self.api_base = os.getenv("LOCAL_MODEL_API", "http://localhost:1234/v1")
        self.use_local_model = bool(os.getenv("LOCAL_MODEL_API")) and "api.openai.com" not in self.api_base
        
        if settings.openai_api_key or self.use_local_model:
            from openai import OpenAI
            # LM Studio requires 'lm-studio' as the key if auth is enabled, 
            # or it might complain if the key looks like a placeholder.
            # In your log it suggests 'sk-lm-...' so we'll try to be flexible.
            api_key = settings.openai_api_key
            if self.use_local_model and (not api_key or "not-needed" in api_key):
                api_key = "lm-studio"
                
            self.client = OpenAI(
                api_key=api_key,
                base_url=self.api_base if self.use_local_model else None,
            )
            if self.use_local_model:
                print(f"  [MODEL] Using local OpenAI-compatible endpoint: {self.api_base}", flush=True)
        else:
            self.client = None

    def _record_usage(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        prompt_tokens = getattr(usage, "prompt_tokens", None)
        if prompt_tokens is None:
            prompt_tokens = getattr(usage, "input_tokens", 0)

        completion_tokens = getattr(usage, "completion_tokens", None)
        if completion_tokens is None:
            completion_tokens = getattr(usage, "output_tokens", 0)

        total_tokens = getattr(usage, "total_tokens", None)
        if total_tokens is None:
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

        self.usage_totals["prompt_tokens"] += int(prompt_tokens or 0)
        self.usage_totals["completion_tokens"] += int(completion_tokens or 0)
        self.usage_totals["total_tokens"] += int(total_tokens or 0)
        self.usage_totals["requests"] += 1
        self.usage_available = True

    def print_usage_summary(self) -> None:
        if not self.usage_available:
            print("Token usage: unavailable from model/backend response.", flush=True)
            return

        print(
            "Token usage: "
            f"{self.usage_totals['total_tokens']} total "
            f"({self.usage_totals['prompt_tokens']} prompt, "
            f"{self.usage_totals['completion_tokens']} completion) "
            f"across {self.usage_totals['requests']} request(s).",
            flush=True,
        )

    def _fallback_plan(self, product: ProductInput) -> ListingPlan:
        title = product.product_id
        desc_parts = [f"Automatycznie wygenerowana oferta: {product.product_id}."]
        if product.facts:
            facts_text = "\n".join(f"{key}: {value}" for key, value in product.facts.items())
            desc_parts.append(f"Fakty o produkcie:\n{facts_text}")
        if product.optional_text:
            desc_parts.append(product.optional_text)

        return ListingPlan(
            product_id=product.product_id,
            title=title,
            description="\n\n".join(desc_parts),
            price=99.0,
            currency=self.settings.default_currency,
            category="Dom i Ogród",
            condition="Używany",
            attributes={"source": "fallback"},
            image_paths=[str(p) for p in product.image_paths],
            cover_image=str(product.image_paths[0]) if product.image_paths else None,
        )

    def analyze(self, product: ProductInput) -> ListingPlan:
        if not self.client:
            return self._fallback_plan(product)

        # Try different image counts to manage local model context limits
        counts_to_try = [4, 2, 1] if self.use_local_model else [len(product.image_paths)]
        
        for count in counts_to_try:
            image_blocks = []
            selected_paths = product.image_paths[:count]
            print(
                f"  [MODEL] Preparing {len(selected_paths)} image(s) for {product.product_id}...",
                flush=True,
            )
            
            for path in selected_paths:
                if self.use_local_model:
                    try:
                        with open(path, "rb") as image_file:
                            data = image_file.read()
                            if len(data) > 3 * 1024 * 1024:
                                continue
                            encoded_string = base64.b64encode(data).decode("utf-8")
                            mime_type = "image/jpeg" if path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
                            image_blocks.append(
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{mime_type};base64,{encoded_string}"},
                                }
                            )
                    except Exception as e:
                        print(f"  [DEBUG] Failed to encode {path}: {e}", flush=True)
                else:
                    image_blocks.append(
                        {
                            "type": "input_image",
                            "image_url": path.resolve().as_uri(),
                        }
                    )

            prompt = (
                "Przeanalizuj produkt ze zdjęć i opcjonalnego opisu.\n"
                "Jeśli podano fakty o produkcie, traktuj je jako ważniejsze niż zgadywanie ze zdjęć. "
                "Użyj ich w opisie, ale nie dopisuj niepotwierdzonych szczegółów.\n"
                "Zwróć WYŁĄCZNIE JSON z polami:\n"
                "- title (max 100 znaków)\n"
                "- description (szczegółowy opis sprzedażowy, postaraj się zeby był precyzyjny, bez 'lania wody')\n"
                "- category (wybierz najbardziej pasującą z listy: Meble, Artykuły gospodarstwa domowego, Ogród, Narzędzia, Gry wideo, Książki, instrumenty muzyczne, Antyki i Kolekcje, Biżuteria i zegarki)\n"
                "- condition (wybierz dokładnie jedno z: Nowy, Jak nowy, Bardzo dobry, Dobry, Do renowacji)\n"
                "- attributes (object)\n"
                "- suggested_price_pln (number)\n"
                "- cover_image_index (number)\n"
                "Opis ma być sprzedażowy po polsku, zachęcający, bez halucynacji."
            )
            if product.facts:
                facts_text = "\n".join(f"- {key}: {value}" for key, value in product.facts.items())
                prompt += f"\n\nFakty podane przy uploadzie:\n{facts_text}"
            if product.optional_text:
                prompt += f"\n\nOpis użytkownika:\n{product.optional_text}"

            try:
                print(
                    f"  [MODEL] Sending request for {product.product_id} with {len(image_blocks)} image(s)...",
                    flush=True,
                )
                started_at = time.monotonic()
                if self.use_local_model:
                    resp = self.client.chat.completions.create(
                        model=self.settings.openai_model,
                        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, *image_blocks]}],
                    )
                    self._record_usage(resp)
                    text = resp.choices[0].message.content.strip()
                else:
                    resp = self.client.responses.create(
                        model=self.settings.openai_model,
                        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, *image_blocks]}],
                    )
                    self._record_usage(resp)
                    text = resp.output_text.strip()
                elapsed = time.monotonic() - started_at
                print(f"  [MODEL] Response received in {elapsed:.1f}s.", flush=True)

                # If we got here, the count worked
                break
            except Exception as e:
                if "context" in str(e).lower() and count > 1:
                    print(f"  [RETRY] Count {count} too large for local model, trying fewer images...", flush=True)
                    continue
                else:
                    print(f"  [ERROR] Model failed at count {count}: {e}", flush=True)
                    return self._fallback_plan(product)

        # Clean up JSON
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            # Try to find anything looking like JSON in the text
            if "{" in text and "}" in text:
                try:
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    payload = json.loads(text[start:end])
                except:
                    return self._fallback_plan(product)
            else:
                return self._fallback_plan(product)

        cover_index = int(payload.get("cover_image_index", 0))
        if cover_index < 0 or cover_index >= len(product.image_paths):
            cover_index = 0

        return ListingPlan(
            product_id=product.product_id,
            title=str(payload.get("title", product.product_id))[:120],
            description=str(payload.get("description", ""))[:8000],
            price=float(payload.get("suggested_price_pln", 99.0)),
            currency="PLN",
            category=str(payload.get("category", "Dom i Ogród")),
            condition=str(payload.get("condition", "Używany")),
            attributes=payload.get("attributes", {}) or {},
            image_paths=[str(p) for p in product.image_paths],
            cover_image=str(product.image_paths[cover_index]) if product.image_paths else None,
        )
