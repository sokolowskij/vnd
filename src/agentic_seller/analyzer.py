from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from .config import Settings
from .models import ListingPlan, ProductInput


class ListingAnalyzer:
    def __init__(self, settings: Settings):
        self.settings = settings
        # In a real local copilot-integrated environment, we might use a local LLM endpoint
        # or a specific environment-provided token. For this request, I will simplify 
        # the analyzer to work with a generic local endpoint (like LM Studio or Ollama)
        # which is the common way to use 'free' models in a dev environment.
        self.api_base = os.getenv("LOCAL_MODEL_API", "http://localhost:1234/v1")
        # Ensure we don't accidentally hit the real OpenAI API if we want local
        is_local = "localhost" in self.api_base or "127.0.0.1" in self.api_base
        
        if settings.openai_api_key or is_local:
            from openai import OpenAI
            # LM Studio requires 'lm-studio' as the key if auth is enabled, 
            # or it might complain if the key looks like a placeholder.
            # In your log it suggests 'sk-lm-...' so we'll try to be flexible.
            api_key = settings.openai_api_key
            if is_local and (not api_key or "not-needed" in api_key):
                api_key = "lm-studio"
                
            self.client = OpenAI(
                api_key=api_key,
                base_url=self.api_base if is_local else None
            )
        else:
            self.client = None

    def _fallback_plan(self, product: ProductInput) -> ListingPlan:
        title = product.product_id
        desc_parts = [f"Automatycznie wygenerowana oferta: {product.product_id}."]
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
        # Check for cached plan first
        listing_path = product.root_dir / "listing_plan.json"
        if listing_path.exists():
            try:
                data = json.loads(listing_path.read_text(encoding="utf-8"))
                # Basic validation to ensure it's not a fallback/empty plan
                if data.get("attributes", {}).get("source") != "fallback":
                    print(f"  [CACHE] Using existing listing plan for {product.product_id}")
                    return ListingPlan(**data)
            except Exception as e:
                print(f"  [DEBUG] Could not load cache: {e}")

        if not self.client:
            return self._fallback_plan(product)

        is_local = "localhost" in self.api_base or "127.0.0.1" in self.api_base
        
        # Try different image counts to manage local model context limits
        counts_to_try = [4, 2, 1] if is_local else [len(product.image_paths)]
        
        for count in counts_to_try:
            image_blocks = []
            selected_paths = product.image_paths[:count]
            
            for path in selected_paths:
                if is_local:
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
                        print(f"  [DEBUG] Failed to encode {path}: {e}")
                else:
                    image_blocks.append(
                        {
                            "type": "input_image",
                            "image_url": path.resolve().as_uri(),
                        }
                    )

            prompt = (
                "Przeanalizuj produkt ze zdjęć i opcjonalnego opisu.\n"
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
            if product.optional_text:
                prompt += f"\n\nOpis użytkownika:\n{product.optional_text}"

            try:
                if is_local:
                    resp = self.client.chat.completions.create(
                        model=self.settings.openai_model,
                        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, *image_blocks]}],
                    )
                    text = resp.choices[0].message.content.strip()
                else:
                    resp = self.client.responses.create(
                        model=self.settings.openai_model,
                        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, *image_blocks]}],
                    )
                    text = resp.output_text.strip()
                
                # If we got here, the count worked
                break
            except Exception as e:
                if "context" in str(e).lower() and count > 1:
                    print(f"  [RETRY] Count {count} too large for local model, trying fewer images...")
                    continue
                else:
                    print(f"  [ERROR] Model failed at count {count}: {e}")
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
