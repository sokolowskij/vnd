"""Streamlit review portal for Agentic Seller."""

from __future__ import annotations

import json
import os
from io import BytesIO
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(page_title="Agentic Seller", layout="wide")

API_URL = os.getenv("API_URL", "http://backend:8000")


def api_get(path: str, **kwargs) -> dict:
    response = requests.get(f"{API_URL}{path}", timeout=15, **kwargs)
    response.raise_for_status()
    return response.json()


def api_post(path: str, **kwargs) -> dict:
    response = requests.post(f"{API_URL}{path}", timeout=60, **kwargs)
    response.raise_for_status()
    return response.json()


def api_put(path: str, **kwargs) -> dict:
    response = requests.put(f"{API_URL}{path}", timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def api_bytes(path: str) -> bytes:
    response = requests.get(f"{API_URL}{path}", timeout=20)
    response.raise_for_status()
    return response.content


def current_user() -> dict | None:
    return st.session_state.get("user")


def logout() -> None:
    st.session_state.pop("user", None)
    st.rerun()


def show_auth() -> None:
    st.title("Agentic Seller")
    st.caption("Product intake and listing approval.")

    try:
        configured = api_get("/auth/status").get("configured", False)
    except requests.exceptions.RequestException as exc:
        st.error(f"Backend unavailable: {exc}")
        st.stop()

    if not configured:
        st.subheader("Create Boss Account")
        with st.form("setup_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Create account")
        if submitted:
            try:
                user = api_post("/auth/setup", json={"username": username, "password": password})
            except requests.exceptions.RequestException as exc:
                st.error(f"Setup failed: {exc}")
            else:
                st.session_state["user"] = user
                st.rerun()
        st.stop()

    st.subheader("Sign In")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        try:
            user = api_post("/auth/login", json={"username": username, "password": password})
        except requests.exceptions.RequestException:
            st.error("Invalid username or password.")
        else:
            st.session_state["user"] = user
            st.rerun()
    st.stop()


def product_badge(status: str) -> str:
    labels = {
        "awaiting_generation": "Awaiting generation",
        "awaiting_review": "Awaiting review",
        "ready_to_publish": "Ready to publish",
    }
    return labels.get(status, status.replace("_", " ").title())


def show_thumbnails(product: dict, max_images: int = 8) -> None:
    images = product.get("images", [])[:max_images]
    if not images:
        st.info("No photos uploaded.")
        return

    columns = st.columns(min(4, len(images)))
    for index, image_name in enumerate(images):
        with columns[index % len(columns)]:
            try:
                content = api_bytes(f"/products/{product['product_id']}/files/{image_name}")
            except requests.exceptions.RequestException:
                st.warning(image_name)
            else:
                st.image(BytesIO(content), caption=image_name, use_container_width=True)


def rotate_product_image(product: dict, image_name: str, degrees: int) -> None:
    api_post(
        f"/products/{product['product_id']}/files/{image_name}/rotate",
        json={"degrees": degrees},
    )


def show_review_images(product: dict, max_images: int = 8) -> None:
    images = product.get("images", [])[:max_images]
    if not images:
        st.info("No photos uploaded.")
        return

    columns = st.columns(min(4, len(images)))
    for index, image_name in enumerate(images):
        with columns[index % len(columns)]:
            try:
                content = api_bytes(f"/products/{product['product_id']}/files/{image_name}")
            except requests.exceptions.RequestException:
                st.warning(image_name)
                continue

            st.image(BytesIO(content), caption=image_name, use_container_width=True)
            left, right = st.columns(2)
            if left.button("Rotate left", key=f"rotate_left_{product['product_id']}_{image_name}"):
                try:
                    rotate_product_image(product, image_name, -90)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Rotation failed: {exc}")
                else:
                    st.rerun()
            if right.button("Rotate right", key=f"rotate_right_{product['product_id']}_{image_name}"):
                try:
                    rotate_product_image(product, image_name, 90)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Rotation failed: {exc}")
                else:
                    st.rerun()


def show_preview_image(product: dict) -> None:
    images = product.get("images", [])
    if not images:
        st.caption("No preview")
        return

    image_name = images[0]
    try:
        content = api_bytes(f"/products/{product['product_id']}/files/{image_name}")
    except requests.exceptions.RequestException:
        st.caption("Preview unavailable")
    else:
        st.image(BytesIO(content), caption=image_name, use_container_width=True)


def format_price(product: dict) -> str:
    price = product.get("price")
    if not isinstance(price, (int, float)):
        return "-"
    currency = (product.get("listing") or {}).get("currency", "PLN")
    return f"{price:.0f} {currency}"


def show_product_details(product: dict, key_prefix: str) -> None:
    listing = product.get("listing") or {}

    meta_cols = st.columns(4)
    meta_cols[0].write(f"Status: **{product_badge(product['status'])}**")
    meta_cols[1].write(f"Category: **{product.get('category') or '-'}**")
    meta_cols[2].write(f"Price: **{format_price(product)}**")
    meta_cols[3].write(f"Added by: **{product.get('added_by') or '-'}**")

    if product.get("approved_by"):
        st.caption(f"Approved by {product['approved_by']}")

    description = listing.get("description", "")
    if description:
        st.text_area(
            "Description",
            value=description,
            height=180,
            disabled=True,
            key=f"{key_prefix}_description",
        )
    else:
        st.info("No generated description yet.")

    show_thumbnails(product, max_images=8)


def product_table(products: list[dict], key_prefix: str) -> None:
    if not products:
        st.info("No items yet.")
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
                        f"Added by: {product.get('added_by') or '-'}",
                        product.get("category") or "No category",
                        format_price(product),
                    ]
                )
            )
            with st.expander("Open product details"):
                show_product_details(product, f"{key_prefix}_{product['product_id']}")


def upload_page() -> None:
    st.header("Upload Items")
    left, right = st.columns([2, 1])

    with left:
        with st.form("upload_product_form", clear_on_submit=True):
            product_name = st.text_input("Item name")
            notes = st.text_area("Notes", height=120)
            files = st.file_uploader(
                "Photos and documents",
                type=["jpg", "jpeg", "png", "webp", "txt", "md", "docx"],
                accept_multiple_files=True,
            )
            submitted = st.form_submit_button("Upload")

    with right:
        st.metric("Accepted formats", "JPG PNG WEBP")
        st.metric("Listing source", "Local runner")

    if submitted:
        if not product_name.strip():
            st.error("Item name is required.")
        elif not files:
            st.error("Add at least one photo or document.")
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
                    },
                    files=multipart_files,
                )
            except requests.exceptions.RequestException as exc:
                st.error(f"Upload failed: {exc}")
            else:
                st.success(f"Uploaded {result['product_id']}")


def items_page() -> None:
    st.header("Items")
    try:
        products = api_get("/products").get("products", [])
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load items: {exc}")
        return

    pending = [p for p in products if p["status"] != "ready_to_publish"]
    ready = [p for p in products if p["status"] == "ready_to_publish"]

    col1, col2, col3 = st.columns(3)
    col1.metric("In review", len(pending))
    col2.metric("Ready", len(ready))
    col3.metric("All items", len(products))

    tab_pending, tab_ready = st.tabs(["In Review", "Ready"])
    with tab_pending:
        product_table(pending, "pending")
    with tab_ready:
        product_table(ready, "ready")


def review_page() -> None:
    st.header("Boss Review")

    try:
        products = api_get("/products").get("products", [])
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load items: {exc}")
        return

    reviewable = [p for p in products if p["status"] != "ready_to_publish"]
    if not reviewable:
        st.info("No items waiting for review.")
        return

    options = {f"{p['title']} ({product_badge(p['status'])})": p["product_id"] for p in reviewable}
    selected_label = st.selectbox("Item", list(options.keys()))
    product_id = options[selected_label]

    try:
        product = api_get(f"/products/{product_id}")
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not load item: {exc}")
        return

    left, right = st.columns([1.1, 1])
    with left:
        show_review_images(product)

    listing = product.get("listing") or {}
    image_paths = listing.get("image_paths") or []
    current_cover = listing.get("cover_image")
    attributes = listing.get("attributes") or {}

    with right:
        st.write(f"Status: **{product_badge(product['status'])}**")
        st.write(f"Added by: **{product.get('added_by') or '-'}**")
        if not listing:
            st.warning("No generated listing yet. Run the local generator, then sync or refresh this item.")

        with st.form(f"review_form_{product_id}"):
            title = st.text_input("Title", value=listing.get("title", product["product_id"]))
            price = st.number_input("Price", min_value=0.0, value=float(listing.get("price") or 0.0), step=1.0)
            currency = st.text_input("Currency", value=listing.get("currency", "PLN"))
            category = st.text_input("Category", value=listing.get("category", ""))
            condition = st.text_input("Condition", value=listing.get("condition", ""))
            description = st.text_area("Description", value=listing.get("description", ""), height=240)
            attrs_text = st.text_area(
                "Attributes JSON",
                value=json.dumps(attributes, ensure_ascii=False, indent=2),
                height=140,
            )
            cover_options = image_paths or [str(product["product_dir"] + "/" + name) for name in product.get("images", [])]
            cover_index = cover_options.index(current_cover) if current_cover in cover_options else 0
            cover_image = (
                st.selectbox("Cover image", cover_options, index=cover_index, format_func=lambda path: Path(path).name)
                if cover_options
                else None
            )

            save_clicked = st.form_submit_button("Save Changes")

        if save_clicked:
            try:
                parsed_attrs = json.loads(attrs_text) if attrs_text.strip() else {}
            except json.JSONDecodeError as exc:
                st.error(f"Attributes must be valid JSON: {exc}")
            else:
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
                    api_put(f"/products/{product_id}/listing", json=payload)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Save failed: {exc}")
                else:
                    st.success("Saved.")
                    st.rerun()

        if listing and st.button("Approve For Publishing", type="primary"):
            try:
                api_post(f"/products/{product_id}/approve", data={"username": current_user()["username"]})
            except requests.exceptions.RequestException as exc:
                st.error(f"Approval failed: {exc}")
            else:
                st.success("Approved and moved to ready.")
                st.rerun()


def users_page() -> None:
    st.header("Users")
    with st.form("create_user_form"):
        username = st.text_input("New username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["user", "boss"])
        submitted = st.form_submit_button("Create user")
    if submitted:
        try:
            api_post("/auth/users", json={"username": username, "password": password, "role": role})
        except requests.exceptions.RequestException as exc:
            st.error(f"Could not create user: {exc}")
        else:
            st.success(f"Created {username}")


if current_user() is None:
    show_auth()

user = current_user()
st.sidebar.title("Agentic Seller")
st.sidebar.caption(f"{user['username']} | {user['role']}")

pages = ["Items", "Upload"]
if user["role"] == "boss":
    pages.extend(["Boss Review", "Users"])
page = st.sidebar.radio("Workspace", pages)

st.sidebar.divider()
if st.sidebar.button("Sign out"):
    logout()

if page == "Items":
    items_page()
elif page == "Upload":
    upload_page()
elif page == "Boss Review":
    review_page()
elif page == "Users":
    users_page()
