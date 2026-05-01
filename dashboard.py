"""Streamlit review portal for Agentic Seller."""

from __future__ import annotations

import json
import os
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
import streamlit as st
from streamlit.components.v1 import html

st.set_page_config(page_title="Agentic Seller", layout="wide")

API_URL = os.getenv("API_URL", "http://backend:8000")
SHOP_OPTIONS = ["", "KC", "FW", "KEN", "MAG"]
PACKAGE_SIZE_OPTIONS = ["small", "medium", "large"]
DEFAULT_MARKETPLACES = ["facebook", "olx", "vinted"]
FACT_FIELDS = [
    ("brand", "Brand"),
    ("maker", "Maker"),
    ("model", "Model"),
    ("year", "Year"),
    ("material", "Material"),
    ("color", "Color"),
    ("dimensions", "Dimensions"),
]
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "agentic_seller_session")
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))
SESSION_MAX_AGE_SECONDS = SESSION_TTL_DAYS * 24 * 60 * 60
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}
TRANSLATIONS = {
    "pl": {
        "Product intake and listing approval.": "Dodawanie produktów i akceptacja ogłoszeń.",
        "Create Boss Account": "Utwórz konto szefa",
        "Username": "Nazwa użytkownika",
        "Password": "Hasło",
        "Create account": "Utwórz konto",
        "Sign In": "Zaloguj",
        "Sign in": "Zaloguj",
        "Invalid username or password.": "Nieprawidłowa nazwa użytkownika lub hasło.",
        "Awaiting generation": "Czeka na generowanie",
        "Awaiting review": "Czeka na akceptację",
        "Ready to publish": "Gotowe do publikacji",
        "No photos uploaded.": "Brak zdjęć.",
        "Rotate left": "Obróć w lewo",
        "Rotate right": "Obróć w prawo",
        "No preview": "Brak podglądu",
        "Preview unavailable": "Podgląd niedostępny",
        "No reviewed items yet.": "Brak zaakceptowanych produktów.",
        "Item": "Produkt",
        "Price": "Cena",
        "Status": "Status",
        "Yes": "Tak",
        "No": "Nie",
        "Send back to review": "Cofnij do akceptacji",
        "Moved back to awaiting review.": "Przeniesiono z powrotem do akceptacji.",
        "Product actions": "Akcje produktu",
        "Prepare download": "Przygotuj pobieranie",
        "Download product data": "Pobierz dane produktu",
        "Confirm delete": "Potwierdź usunięcie",
        "Delete product": "Usuń produkt",
        "Deleted.": "Usunięto.",
        "Category": "Kategoria",
        "Added by": "Dodał",
        "Added at": "Dodano",
        "Shop": "Sklep",
        "Package": "Paczka",
        "Approved by": "Zatwierdził",
        "LLM notes": "Notatki dla LLM",
        "Marketplace presence": "Obecność na marketplace",
        "URL": "URL",
        "Notes": "Notatki",
        "Add marketplace": "Dodaj marketplace",
        "Listed there": "Wystawione tam",
        "Listing URL": "URL ogłoszenia",
        "Marketplace notes": "Notatki marketplace",
        "Marketplace added.": "Marketplace dodany.",
        "Marketplace status saved.": "Status marketplace zapisany.",
        "Description": "Opis",
        "No generated description yet.": "Brak wygenerowanego opisu.",
        "No items yet.": "Brak produktów.",
        "Open product details": "Otwórz szczegóły produktu",
        "No category": "Brak kategorii",
        "Upload Items": "Dodaj produkty",
        "Photos and documents": "Zdjęcia i dokumenty",
        "Item name": "Nazwa produktu",
        "Package size": "Rozmiar paczki",
        "Actual store shelf price": "Rzeczywista cena na półce",
        "Optional product facts": "Opcjonalne fakty o produkcie",
        "Brand": "Marka",
        "Maker": "Producent",
        "Model": "Model",
        "Year": "Rok",
        "Material": "Materiał",
        "Color": "Kolor",
        "Dimensions": "Wymiary",
        "Optional notes from documents or seller": "Opcjonalne notatki z dokumentów lub od sprzedawcy",
        "Optional additional notes for LLM agent": "Opcjonalne dodatkowe notatki dla agenta LLM",
        "Upload": "Dodaj",
        "Uploaded": "Dodano",
        "Accepted formats": "Akceptowane formaty",
        "Listing source": "Źródło ogłoszeń",
        "Local runner": "Lokalny runner",
        "Item name is required.": "Nazwa produktu jest wymagana.",
        "Add at least one photo or document.": "Dodaj co najmniej jedno zdjęcie lub dokument.",
        "Items": "Produkty",
        "Could not load items": "Nie można załadować produktów",
        "In review": "W akceptacji",
        "Ready": "Gotowe",
        "All items": "Wszystkie produkty",
        "In Review": "W akceptacji",
        "Reviewed items": "Zaakceptowane produkty",
        "Boss Review": "Akceptacja szefa",
        "No items available.": "Brak produktów.",
        "No generated listing yet. Run the local generator, then sync or refresh this item.": "Brak wygenerowanego ogłoszenia. Uruchom lokalne generowanie, potem zsynchronizuj lub odśwież produkt.",
        "Title": "Tytuł",
        "Currency": "Waluta",
        "Condition": "Stan",
        "Product facts": "Fakty o produkcie",
        "Additional notes for LLM agent": "Dodatkowe notatki dla agenta LLM",
        "Cover image": "Zdjęcie główne",
        "Save Changes": "Zapisz zmiany",
        "Saved.": "Zapisano.",
        "Approve For Publishing": "Zatwierdź do publikacji",
        "Approved and moved to ready.": "Zatwierdzono i przeniesiono do gotowych.",
        "Users": "Użytkownicy",
        "New username": "Nowa nazwa użytkownika",
        "Role": "Rola",
        "Create user": "Utwórz użytkownika",
        "Data retention": "Retencja danych",
        "Prepare full export": "Przygotuj pełny eksport",
        "Download all product data": "Pobierz wszystkie dane produktów",
        "Run retention cleanup": "Uruchom czyszczenie retencji",
        "Daily email backup": "Codzienna kopia e-mail",
        "Send backup email now": "Wyślij kopię e-mail teraz",
        "Logout": "Wyloguj",
        "Language": "Język",
        "Workspace": "Obszar",
        "Switch to Polish": "Przełącz na polski",
        "Switch to English": "Przełącz na angielski",
    }
}


def current_language() -> str:
    return st.session_state.get("language", "en")


def T(text: str) -> str:
    return TRANSLATIONS.get(current_language(), {}).get(text, text)


def auth_request_kwargs(kwargs: dict) -> dict:
    headers = dict(kwargs.pop("headers", {}) or {})
    token = st.session_state.get("session_token")
    if token:
        headers.setdefault("Authorization", f"Bearer {token}")
    if headers:
        kwargs["headers"] = headers
    return kwargs


def api_get(path: str, **kwargs) -> dict:
    kwargs = auth_request_kwargs(kwargs)
    response = requests.get(f"{API_URL}{path}", timeout=15, **kwargs)
    response.raise_for_status()
    return response.json()


def api_post(path: str, **kwargs) -> dict:
    kwargs = auth_request_kwargs(kwargs)
    response = requests.post(f"{API_URL}{path}", timeout=60, **kwargs)
    response.raise_for_status()
    return response.json()


def api_put(path: str, **kwargs) -> dict:
    kwargs = auth_request_kwargs(kwargs)
    response = requests.put(f"{API_URL}{path}", timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def api_delete(path: str, **kwargs) -> dict:
    kwargs = auth_request_kwargs(kwargs)
    response = requests.delete(f"{API_URL}{path}", timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def api_bytes(path: str) -> bytes:
    response = requests.get(f"{API_URL}{path}", timeout=20, **auth_request_kwargs({}))
    response.raise_for_status()
    return response.content


def api_error_message(exc: requests.exceptions.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return str(exc)
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = response.text.strip()
    return f"{exc} ({detail})" if detail else str(exc)


def format_datetime(value: str | None) -> str:
    if not value:
        return "-"
    return value.replace("T", " ")[:16]


def product_file_path(product: dict, image_name: str) -> str:
    return f"/products/{quote(product['product_id'])}/files/{quote(image_name)}"


def current_user() -> dict | None:
    return st.session_state.get("user")


def browser_session_cookie() -> str | None:
    context = getattr(st, "context", None)
    cookies = getattr(context, "cookies", {}) if context is not None else {}
    token = cookies.get(SESSION_COOKIE_NAME) if hasattr(cookies, "get") else None
    return token or None


def write_session_cookie(token: str) -> None:
    secure = "; Secure" if SESSION_COOKIE_SECURE else ""
    html(
        f"""
        <script>
        const cookieName = {json.dumps(SESSION_COOKIE_NAME)};
        const cookieValue = encodeURIComponent({json.dumps(token)});
        document.cookie = `${{cookieName}}=${{cookieValue}}; Max-Age={SESSION_MAX_AGE_SECONDS}; Path=/; SameSite=Lax{secure}`;
        window.parent.location.reload();
        </script>
        """,
        height=0,
    )


def clear_session_cookie(reload_page: bool = True) -> None:
    reload_script = "window.parent.location.reload();" if reload_page else ""
    secure = "; Secure" if SESSION_COOKIE_SECURE else ""
    html(
        f"""
        <script>
        const cookieName = {json.dumps(SESSION_COOKIE_NAME)};
        document.cookie = `${{cookieName}}=; Max-Age=0; Path=/; SameSite=Lax{secure}`;
        {reload_script}
        </script>
        """,
        height=0,
    )


def user_from_auth_payload(payload: dict) -> dict:
    return {"username": payload["username"], "role": payload.get("role", "user")}


def start_authenticated_session(payload: dict) -> None:
    token = payload.get("session_token")
    st.session_state["user"] = user_from_auth_payload(payload)
    if token:
        st.session_state["session_token"] = token
        write_session_cookie(token)
        st.stop()
    st.rerun()


def restore_session_from_cookie() -> None:
    if current_user() is not None:
        return
    token = browser_session_cookie()
    if not token:
        return

    st.session_state["session_token"] = token
    try:
        user = api_get("/auth/session")
    except requests.exceptions.RequestException:
        st.session_state.pop("session_token", None)
        st.session_state.pop("user", None)
        clear_session_cookie(reload_page=False)
    else:
        st.session_state["user"] = user_from_auth_payload(user)


def logout() -> None:
    try:
        api_post("/auth/logout")
    except requests.exceptions.RequestException:
        pass
    st.session_state.pop("user", None)
    st.session_state.pop("session_token", None)
    clear_session_cookie()
    st.stop()


def show_auth() -> None:
    st.title("Agentic Seller")
    st.caption(T("Product intake and listing approval."))
    next_language = "pl" if current_language() == "en" else "en"
    if st.button(T("Switch to Polish") if next_language == "pl" else T("Switch to English")):
        st.session_state["language"] = next_language
        st.rerun()

    try:
        configured = api_get("/auth/status").get("configured", False)
    except requests.exceptions.RequestException as exc:
        st.error(f"Backend unavailable: {exc}")
        st.stop()

    if not configured:
        st.subheader(T("Create Boss Account"))
        with st.form("setup_form"):
            username = st.text_input(T("Username"))
            password = st.text_input(T("Password"), type="password")
            submitted = st.form_submit_button(T("Create account"))
        if submitted:
            try:
                user = api_post("/auth/setup", json={"username": username, "password": password})
            except requests.exceptions.RequestException as exc:
                st.error(f"Setup failed: {exc}")
            else:
                start_authenticated_session(user)
        st.stop()

    st.subheader(T("Sign In"))
    with st.form("login_form"):
        username = st.text_input(T("Username"))
        password = st.text_input(T("Password"), type="password")
        submitted = st.form_submit_button(T("Sign in"))
    if submitted:
        try:
            user = api_post("/auth/login", json={"username": username, "password": password})
        except requests.exceptions.RequestException:
            st.error(T("Invalid username or password."))
        else:
            start_authenticated_session(user)
    st.stop()


def product_badge(status: str) -> str:
    labels = {
        "awaiting_generation": T("Awaiting generation"),
        "awaiting_review": T("Awaiting review"),
        "ready_to_publish": T("Ready to publish"),
    }
    return labels.get(status, status.replace("_", " ").title())


def show_thumbnails(product: dict, max_images: int = 8) -> None:
    images = product.get("images", [])[:max_images]
    if not images:
        st.info(T("No photos uploaded."))
        return

    columns = st.columns(min(4, len(images)))
    for index, image_name in enumerate(images):
        with columns[index % len(columns)]:
            try:
                content = api_bytes(product_file_path(product, image_name))
            except requests.exceptions.RequestException:
                st.warning(image_name)
            else:
                st.image(BytesIO(content), caption=image_name, use_container_width=True)


def rotate_product_image(product: dict, image_name: str, degrees: int) -> None:
    api_post(
        f"/products/{quote(product['product_id'])}/files/rotate",
        json={"filename": image_name, "degrees": degrees},
    )


def show_review_images(product: dict, max_images: int = 8) -> None:
    images = product.get("images", [])[:max_images]
    if not images:
        st.info(T("No photos uploaded."))
        return

    columns = st.columns(min(2, len(images)))
    for index, image_name in enumerate(images):
        with columns[index % len(columns)]:
            try:
                content = api_bytes(product_file_path(product, image_name))
            except requests.exceptions.RequestException:
                st.warning(image_name)
                continue

            st.image(BytesIO(content), caption=image_name, use_container_width=True)
            left, right = st.columns(2)
            if left.button(
                "↺",
                key=f"rotate_left_{product['product_id']}_{image_name}",
                help=T("Rotate left"),
                use_container_width=True,
            ):
                try:
                    rotate_product_image(product, image_name, -90)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Rotation failed: {api_error_message(exc)}")
                else:
                    st.rerun()
            if right.button(
                "↻",
                key=f"rotate_right_{product['product_id']}_{image_name}",
                help=T("Rotate right"),
                use_container_width=True,
            ):
                try:
                    rotate_product_image(product, image_name, 90)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Rotation failed: {api_error_message(exc)}")
                else:
                    st.rerun()


def show_preview_image(product: dict) -> None:
    images = product.get("images", [])
    if not images:
        st.caption(T("No preview"))
        return

    image_name = images[0]
    try:
        content = api_bytes(product_file_path(product, image_name))
    except requests.exceptions.RequestException:
        st.caption(T("Preview unavailable"))
    else:
        st.image(BytesIO(content), caption=image_name, use_container_width=True)


def format_price(product: dict) -> str:
    price = product.get("price")
    if not isinstance(price, (int, float)):
        return "-"
    currency = (product.get("listing") or {}).get("currency", "PLN")
    return f"{price:.0f} {currency}"


def option_index(options: list[str], value: str | None, default: int = 0) -> int:
    return options.index(value) if value in options else default


def product_archive_name(product: dict) -> str:
    return f"{product['product_id']}.zip"


def product_download_path(product: dict) -> str:
    return f"/products/{quote(product['product_id'])}/download"


def delete_product(product: dict) -> None:
    api_delete(f"/products/{quote(product['product_id'])}")


def reopen_product(product: dict) -> None:
    api_post(f"/products/{quote(product['product_id'])}/reopen")


def marketplace_label(name: str) -> str:
    labels = {"facebook": "Facebook", "olx": "OLX", "vinted": "Vinted"}
    return labels.get(name, name.replace("_", " ").title())


def marketplace_names(products: list[dict]) -> list[str]:
    names = list(DEFAULT_MARKETPLACES)
    for product in products:
        for name in (product.get("marketplaces") or {}).keys():
            if name not in names:
                names.append(name)
    return names


def marketplace_listed(product: dict, marketplace: str) -> bool:
    status = (product.get("marketplaces") or {}).get(marketplace) or {}
    return bool(status.get("listed"))


def update_product_marketplace(product: dict, marketplace: str, listed: bool, url: str = "", notes: str = "") -> None:
    api_put(
        f"/products/{quote(product['product_id'])}/marketplaces/{quote(marketplace, safe='')}",
        json={"listed": listed, "url": url, "notes": notes},
    )


def reviewed_marketplace_table(products: list[dict]) -> None:
    if not products:
        st.info(T("No reviewed items yet."))
        return

    names = marketplace_names(products)
    rows = []
    for product in products:
        row = {
            T("Item"): product.get("title") or product["product_id"],
            T("Price"): format_price(product),
            T("Status"): product_badge(product["status"]),
        }
        for name in names:
            row[marketplace_label(name)] = T("Yes") if marketplace_listed(product, name) else T("No")
        rows.append(row)
    st.dataframe(rows, use_container_width=True, hide_index=True)


def show_product_actions(product: dict, key_prefix: str) -> None:
    if current_user()["role"] != "boss":
        return

    with st.expander(T("Product actions")):
        if product.get("status") == "ready_to_publish":
            if st.button(T("Send back to review"), key=f"{key_prefix}_reopen"):
                try:
                    reopen_product(product)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Could not send back: {api_error_message(exc)}")
                else:
                    st.success(T("Moved back to awaiting review."))
                    st.rerun()

        download_key = f"{key_prefix}_download_data"
        if st.button(T("Prepare download"), key=f"{key_prefix}_prepare_download"):
            try:
                st.session_state[download_key] = api_bytes(product_download_path(product))
            except requests.exceptions.RequestException as exc:
                st.error(f"Download unavailable: {api_error_message(exc)}")

        if download_key in st.session_state:
            st.download_button(
                T("Download product data"),
                data=st.session_state[download_key],
                file_name=product_archive_name(product),
                mime="application/zip",
                key=f"{key_prefix}_download",
            )

        confirm = st.checkbox(T("Confirm delete"), key=f"{key_prefix}_confirm_delete")
        if st.button(T("Delete product"), disabled=not confirm, key=f"{key_prefix}_delete"):
            try:
                delete_product(product)
            except requests.exceptions.RequestException as exc:
                st.error(f"Delete failed: {api_error_message(exc)}")
            else:
                st.success(T("Deleted."))
                st.rerun()


def show_product_details(product: dict, key_prefix: str) -> None:
    listing = product.get("listing") or {}

    meta_cols = st.columns(4)
    meta_cols[0].write(f"{T('Status')}: **{product_badge(product['status'])}**")
    meta_cols[1].write(f"{T('Category')}: **{product.get('category') or '-'}**")
    meta_cols[2].write(f"{T('Price')}: **{format_price(product)}**")
    meta_cols[3].write(f"{T('Added by')}: **{product.get('added_by') or '-'}**")

    ops_cols = st.columns(3)
    ops_cols[0].write(f"{T('Shop')}: **{product.get('shop') or '-'}**")
    ops_cols[1].write(f"{T('Package')}: **{product.get('package_size') or '-'}**")
    ops_cols[2].write(f"{T('Added at')}: **{format_datetime(product.get('item_added_at'))}**")

    if product.get("approved_by"):
        st.caption(f"{T('Approved by')} {product['approved_by']}")

    facts = [f"{label}: {product.get(field)}" for field, label in FACT_FIELDS if product.get(field)]
    if facts:
        st.caption(" | ".join(facts))
    if product.get("llm_notes"):
        st.caption(f"{T('LLM notes')}: {product['llm_notes']}")

    with st.expander(T("Marketplace presence")):
        marketplaces = product.get("marketplaces") or {}
        for name in marketplace_names([product]):
            current = marketplaces.get(name) or {}
            with st.form(f"{key_prefix}_marketplace_{name}"):
                cols = st.columns([1, 1, 2])
                listed = cols[0].checkbox(
                    marketplace_label(name),
                    value=bool(current.get("listed")),
                    key=f"{key_prefix}_{name}_listed",
                )
                url = cols[1].text_input(
                    T("URL"),
                    value=current.get("url") or "",
                    key=f"{key_prefix}_{name}_url",
                )
                notes = cols[2].text_input(
                    T("Notes"),
                    value=current.get("notes") or "",
                    key=f"{key_prefix}_{name}_notes",
                )
                if st.form_submit_button(f"{T('Save Changes')} {marketplace_label(name)}"):
                    try:
                        update_product_marketplace(product, name, listed, url, notes)
                    except requests.exceptions.RequestException as exc:
                        st.error(f"Marketplace update failed: {api_error_message(exc)}")
                    else:
                        st.success(T("Marketplace status saved."))
                        st.rerun()

        with st.form(f"{key_prefix}_add_marketplace"):
            custom_name = st.text_input(T("Add marketplace"))
            custom_listed = st.checkbox(T("Listed there"), value=True)
            custom_url = st.text_input(T("Listing URL"))
            custom_notes = st.text_input(T("Marketplace notes"))
            if st.form_submit_button(T("Add marketplace")):
                try:
                    update_product_marketplace(product, custom_name, custom_listed, custom_url, custom_notes)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Marketplace update failed: {api_error_message(exc)}")
                else:
                    st.success(T("Marketplace added."))
                    st.rerun()

    description = listing.get("description", "")
    if description:
        st.text_area(
            T("Description"),
            value=description,
            height=180,
            disabled=True,
            key=f"{key_prefix}_description",
        )
    else:
        st.info(T("No generated description yet."))

    show_thumbnails(product, max_images=8)
    show_product_actions(product, key_prefix)


def product_table(products: list[dict], key_prefix: str) -> None:
    if not products:
        st.info(T("No items yet."))
        return

    for product in products:
        st.divider()
        cols = st.columns([1, 3])
        with cols[0]:
            show_preview_image(product)
        with cols[1]:
            st.write(f"**{product['title']}**")
            st.caption(
                " | ".join(
                    [
                        product_badge(product["status"]),
                        f"{T('Added by')}: {product.get('added_by') or '-'}",
                        f"{T('Added at')}: {format_datetime(product.get('item_added_at'))}",
                        product.get("category") or T("No category"),
                        format_price(product),
                    ]
                )
            )
            with st.expander(T("Open product details")):
                show_product_details(product, f"{key_prefix}_{product['product_id']}")


def upload_page() -> None:
    st.header(T("Upload Items"))
    left, right = st.columns([2, 1])

    with left:
        with st.form("upload_product_form", clear_on_submit=True):
            files = st.file_uploader(
                T("Photos and documents"),
                type=["jpg", "jpeg", "png", "webp", "txt", "md", "docx"],
                accept_multiple_files=True,
            )
            product_name = st.text_input(T("Item name"))
            form_cols = st.columns(2)
            shop = form_cols[0].selectbox(T("Shop"), SHOP_OPTIONS)
            package_size = form_cols[1].selectbox(
                T("Package size"),
                PACKAGE_SIZE_OPTIONS,
                index=option_index(PACKAGE_SIZE_OPTIONS, "medium"),
            )
            st.write(T("Optional product facts"))
            fact_cols = st.columns(3)
            upload_facts = {}
            for index, (field, label) in enumerate(FACT_FIELDS):
                upload_facts[field] = fact_cols[index % len(fact_cols)].text_input(T(label))
            notes = st.text_area(T("Optional notes from documents or seller"), height=90)
            llm_notes = st.text_area(T("Optional additional notes for LLM agent"), height=90)
            submitted = st.form_submit_button(T("Upload"))

    with right:
        st.metric(T("Accepted formats"), "JPG PNG WEBP")
        st.metric(T("Listing source"), T("Local runner"))

    if submitted:
        if not product_name.strip():
            st.error(T("Item name is required."))
        elif not files:
            st.error(T("Add at least one photo or document."))
        else:
            multipart_files = [
                ("files", (file.name, file.getvalue(), file.type or "application/octet-stream"))
                for file in files
            ]
            try:
                result = api_post(
                    "/uploads/products",
                    data={
                        "product_name": product_name,
                        "notes": notes,
                        "added_by": current_user()["username"],
                        "shop": shop,
                        "package_size": package_size,
                        "llm_notes": llm_notes,
                        **upload_facts,
                    },
                    files=multipart_files,
                )
            except requests.exceptions.RequestException as exc:
                st.error(f"Upload failed: {exc}")
            else:
                st.success(f"{T('Uploaded')} {result['product_id']}")


def items_page() -> None:
    st.header(T("Items"))
    try:
        products = api_get("/products").get("products", [])
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load items: {exc}")
        return

    pending = [p for p in products if p["status"] != "ready_to_publish"]
    ready = [p for p in products if p["status"] == "ready_to_publish"]

    col1, col2, col3 = st.columns(3)
    col1.metric(T("In review"), len(pending))
    col2.metric(T("Ready"), len(ready))
    col3.metric(T("All items"), len(products))

    tab_pending, tab_ready = st.tabs([T("In Review"), T("Ready")])
    with tab_pending:
        product_table(pending, "pending")
    with tab_ready:
        st.subheader(T("Reviewed items"))
        reviewed_marketplace_table(ready)
        product_table(ready, "ready")


def review_page() -> None:
    st.header(T("Boss Review"))

    try:
        products = api_get("/products").get("products", [])
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load items: {exc}")
        return

    if not products:
        st.info(T("No items available."))
        return

    options = {f"{p['title']} ({product_badge(p['status'])})": p["product_id"] for p in products}
    selected_label = st.selectbox(T("Item"), list(options.keys()))
    product_id = options[selected_label]

    try:
        product = api_get(f"/products/{quote(product_id)}")
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load item: {exc}")
        return

    left, right = st.columns([1, 1])
    with left:
        show_review_images(product)

    listing = product.get("listing") or {}
    image_paths = listing.get("image_paths") or []
    current_cover = listing.get("cover_image")
    attributes = listing.get("attributes") or {}

    with right:
        st.write(f"{T('Status')}: **{product_badge(product['status'])}**")
        st.write(f"{T('Added by')}: **{product.get('added_by') or '-'}**")
        st.write(f"{T('Added at')}: **{format_datetime(product.get('item_added_at'))}**")
        if not listing:
            st.warning(T("No generated listing yet. Run the local generator, then sync or refresh this item."))

        with st.form(f"review_form_{product_id}"):
            meta_cols = st.columns(3)
            shop = meta_cols[0].selectbox(
                T("Shop"),
                SHOP_OPTIONS,
                index=option_index(SHOP_OPTIONS, product.get("shop")),
            )
            package_size = meta_cols[1].selectbox(
                T("Package size"),
                PACKAGE_SIZE_OPTIONS,
                index=option_index(PACKAGE_SIZE_OPTIONS, product.get("package_size"), default=1),
            )
            actual_store_shelf_price = meta_cols[2].number_input(
                T("Actual store shelf price"),
                min_value=0.0,
                value=float(product.get("actual_store_shelf_price") or 0.0),
                step=1.0,
            )
            title = st.text_input(T("Title"), value=listing.get("title", product["product_id"]))
            price = st.number_input(T("Price"), min_value=0.0, value=float(listing.get("price") or 0.0), step=1.0)
            currency = st.text_input(T("Currency"), value=listing.get("currency", "PLN"))
            category = st.text_input(T("Category"), value=listing.get("category", ""))
            condition = st.text_input(T("Condition"), value=listing.get("condition", ""))
            description = st.text_area(T("Description"), value=listing.get("description", ""), height=240)
            st.write(T("Product facts"))
            fact_cols = st.columns(3)
            fact_values = {}
            for index, (field, label) in enumerate(FACT_FIELDS):
                value = product.get(field) or attributes.get(field) or ""
                fact_values[field] = fact_cols[index % len(fact_cols)].text_input(T(label), value=str(value))
            llm_notes = st.text_area(
                T("Additional notes for LLM agent"),
                value=product.get("llm_notes") or "",
                height=90,
            )
            product_image_paths = [str(Path(product["product_dir"]) / name) for name in product.get("images", [])]
            cover_options = product_image_paths or image_paths
            current_cover_name = Path(current_cover).name if current_cover else ""
            cover_names = [Path(path).name for path in cover_options]
            cover_index = cover_names.index(current_cover_name) if current_cover_name in cover_names else 0
            cover_image = (
                st.selectbox(T("Cover image"), cover_options, index=cover_index, format_func=lambda path: Path(path).name)
                if cover_options
                else None
            )

            save_clicked = st.form_submit_button(T("Save Changes"))

        if save_clicked:
            parsed_attrs = {
                key: value
                for key, value in attributes.items()
                if key not in {field for field, _ in FACT_FIELDS}
            }
            parsed_attrs.update({key: value.strip() for key, value in fact_values.items() if value.strip()})
            payload = {
                "title": title,
                "description": description,
                "price": price,
                "currency": currency,
                "category": category,
                "condition": condition,
                "attributes": parsed_attrs,
                "cover_image": cover_image,
            }
            try:
                api_put(f"/products/{quote(product_id)}/listing", json=payload)
                api_put(
                    f"/products/{quote(product_id)}/metadata",
                    json={
                        "shop": shop or None,
                        "package_size": package_size,
                        "actual_store_shelf_price": actual_store_shelf_price,
                        "llm_notes": llm_notes,
                        **fact_values,
                    },
                )
            except requests.exceptions.RequestException as exc:
                st.error(f"Save failed: {api_error_message(exc)}")
            else:
                st.success(T("Saved."))
                st.rerun()

        if product["status"] == "ready_to_publish":
            if st.button(T("Send back to review")):
                try:
                    reopen_product(product)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Could not send back: {api_error_message(exc)}")
                else:
                    st.success(T("Moved back to awaiting review."))
                    st.rerun()
        elif listing and st.button(T("Approve For Publishing"), type="primary"):
            try:
                api_post(f"/products/{quote(product_id)}/approve", data={"username": current_user()["username"]})
            except requests.exceptions.RequestException as exc:
                st.error(f"Approval failed: {exc}")
            else:
                st.success(T("Approved and moved to ready."))
                st.rerun()

        show_product_actions(product, f"review_{product_id}")


def users_page() -> None:
    st.header(T("Users"))
    with st.form("create_user_form"):
        username = st.text_input(T("New username"))
        password = st.text_input(T("Password"), type="password")
        role = st.selectbox(T("Role"), ["user", "boss"])
        submitted = st.form_submit_button(T("Create user"))
    if submitted:
        try:
            api_post("/auth/users", json={"username": username, "password": password, "role": role})
        except requests.exceptions.RequestException as exc:
            st.error(f"Could not create user: {exc}")
        else:
            st.success(f"Created {username}")

    st.divider()
    st.subheader(T("Data retention"))
    try:
        retention = api_get("/admin/retention")
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load retention policy: {api_error_message(exc)}")
        return

    policy = retention.get("policy", {})
    st.caption(
        "Uploaded/in-review items are kept for "
        f"{policy.get('pending_days', '-')} days; ready-to-publish items are kept for "
        f"{policy.get('ready_days', '-')} days. Cleanup runs every "
        f"{policy.get('check_hours', '-')} hours."
    )

    admin_cols = st.columns(2)
    with admin_cols[0]:
        if st.button(T("Prepare full export")):
            try:
                st.session_state["all_product_data_export"] = api_bytes("/admin/data/export")
            except requests.exceptions.RequestException as exc:
                st.error(f"Full export unavailable: {api_error_message(exc)}")

        if "all_product_data_export" in st.session_state:
            st.download_button(
                T("Download all product data"),
                data=st.session_state["all_product_data_export"],
                file_name="agentic-seller-data.zip",
                mime="application/zip",
                key="download_all_data",
            )

    with admin_cols[1]:
        if st.button(T("Run retention cleanup")):
            try:
                result = api_post("/admin/retention/run")
            except requests.exceptions.RequestException as exc:
                st.error(f"Cleanup failed: {api_error_message(exc)}")
            else:
                st.success(f"Deleted {len(result.get('deleted', []))} expired item(s).")
                st.rerun()

    st.divider()
    st.subheader(T("Daily email backup"))
    try:
        backup = api_get("/admin/backup")
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load backup status: {api_error_message(exc)}")
        return

    backup_status = "configured" if backup.get("configured") else "not configured"
    st.caption(
        f"Daily backup is {backup_status}. Scheduled hour: "
        f"{backup.get('hour_utc', '-'):02}:00 UTC."
    )
    st.caption(f"Email attachment limit: {backup.get('max_attachment_mb', '-')} MB.")
    if backup.get("admin_email"):
        st.write(f"Recipient: **{backup['admin_email']}**")
    if backup.get("last_sent_at"):
        st.write(f"Last sent: **{backup['last_sent_at']}**")
    if backup.get("last_error"):
        st.warning(f"Last backup error: {backup['last_error']}")

    if st.button(T("Send backup email now"), disabled=not backup.get("configured")):
        try:
            result = api_post("/admin/backup/run")
        except requests.exceptions.RequestException as exc:
            st.error(f"Backup failed: {api_error_message(exc)}")
        else:
            st.success(f"Backup sent to {result.get('admin_email')}.")
            st.rerun()


restore_session_from_cookie()

if current_user() is None:
    show_auth()

user = current_user()
st.sidebar.title("Agentic Seller")
st.sidebar.caption(f"{user['username']} | {user['role']}")
next_language = "pl" if current_language() == "en" else "en"
language_label = T("Switch to Polish") if next_language == "pl" else T("Switch to English")
if st.sidebar.button(language_label):
    st.session_state["language"] = next_language
    st.rerun()

page_options = ["Items", "Upload"]
if user["role"] == "boss":
    page_options.extend(["Boss Review", "Users"])
page = st.sidebar.radio(T("Workspace"), page_options, format_func=T)

st.sidebar.divider()
if st.sidebar.button(T("Logout")):
    logout()

if page == "Items":
    items_page()
elif page == "Upload":
    upload_page()
elif page == "Boss Review":
    review_page()
elif page == "Users":
    users_page()
