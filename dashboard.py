"""Streamlit dashboard for Agentic Seller job submission and review."""

from __future__ import annotations

import os

import requests
import streamlit as st

st.set_page_config(
    page_title="Agentic Seller Dashboard",
    layout="wide",
)

API_URL = os.getenv("API_URL", "http://backend:8000")

st.title("Agentic Seller Dashboard")
st.caption("Upload product files, run listing jobs, and review status.")


def api_get(path: str) -> dict:
    response = requests.get(f"{API_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(path: str, **kwargs) -> dict:
    response = requests.post(f"{API_URL}{path}", timeout=60, **kwargs)
    response.raise_for_status()
    return response.json()


page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Upload Product", "Submit Job", "Job Details"],
)

if page == "Dashboard":
    st.header("Job Overview")

    try:
        jobs_data = api_get("/jobs")
        jobs = jobs_data.get("jobs", [])
    except requests.exceptions.RequestException as exc:
        st.error(f"Failed to connect to backend: {exc}")
        jobs = []

    if jobs:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pending", sum(1 for job in jobs if job.get("status") == "pending"))
        col2.metric("Running", sum(1 for job in jobs if job.get("status") == "running"))
        col3.metric("Completed", sum(1 for job in jobs if job.get("status") == "completed"))
        col4.metric("Failed", sum(1 for job in jobs if job.get("status") == "failed"))

        st.subheader("Recent Jobs")
        for job in jobs[:10]:
            title = f"{job['job_id'][:8]} | {job['mode']} | {job.get('status', 'unknown')}"
            with st.expander(title):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"Job ID: `{job['job_id']}`")
                    st.write(f"Status: `{job.get('status', 'unknown')}`")
                    st.write(f"Mode: `{job['mode']}`")
                with col2:
                    st.write(f"Created: `{job['created_at']}`")
                    if job.get("completed_at"):
                        st.write(f"Completed: `{job['completed_at']}`")

                st.write(f"Data directory: `{job['data_dir']}`")
                st.write(f"Marketplaces: `{', '.join(job.get('marketplaces', []))}`")
                if job.get("error"):
                    st.error(job["error"])
    else:
        st.info("No jobs yet. Upload a product, then submit a dry-run job.")

    st.header("Uploaded Products")
    try:
        products_data = api_get("/products")
        products = products_data.get("products", [])
    except requests.exceptions.RequestException as exc:
        st.error(f"Failed to load products: {exc}")
        products = []

    if products:
        for product in products:
            with st.expander(product["product_id"]):
                st.write(f"Directory: `{product['product_dir']}`")
                st.write(", ".join(product.get("files", [])) or "No files")
    else:
        st.info("No uploaded products found.")

elif page == "Upload Product":
    st.header("Upload Product")

    with st.form("upload_product_form", clear_on_submit=False):
        product_name = st.text_input("Product name")
        notes = st.text_area("Optional notes", height=120)
        files = st.file_uploader(
            "Photos and optional product notes",
            type=["jpg", "jpeg", "png", "webp", "txt", "md", "docx"],
            accept_multiple_files=True,
        )
        submitted = st.form_submit_button("Upload")

    if submitted:
        if not product_name.strip():
            st.error("Product name is required.")
        elif not files:
            st.error("Select at least one photo or product file.")
        else:
            multipart_files = [
                ("files", (file.name, file.getvalue(), file.type or "application/octet-stream"))
                for file in files
            ]
            data = {"product_name": product_name, "notes": notes}

            try:
                result = api_post("/uploads/products", data=data, files=multipart_files)
            except requests.exceptions.RequestException as exc:
                st.error(f"Upload failed: {exc}")
            else:
                st.success(f"Uploaded `{result['product_id']}` to `{result['product_dir']}`")
                st.write("Saved files:")
                st.write(", ".join(result["saved_files"]))

elif page == "Submit Job":
    st.header("Submit Job")

    try:
        products_data = api_get("/products")
        default_data_dir = products_data.get("data_dir", "/app/data/products")
        products = products_data.get("products", [])
    except requests.exceptions.RequestException:
        default_data_dir = "/app/data/products"
        products = []

    if products:
        st.info(f"{len(products)} uploaded product folder(s) found in `{default_data_dir}`.")
    else:
        st.warning("No uploaded product folders found yet.")

    with st.form("job_form"):
        data_dir = st.text_input("Data directory", value=default_data_dir)
        mode = st.radio("Posting mode", ["dry_run", "publish"])
        marketplaces = st.multiselect(
            "Target marketplaces",
            ["olx", "facebook", "ceneo"],
            default=["olx", "facebook"],
        )
        submitted = st.form_submit_button("Start Job")

    if submitted:
        if not data_dir.strip():
            st.error("Data directory cannot be empty.")
        elif not marketplaces:
            st.error("Select at least one marketplace.")
        else:
            payload = {
                "data_dir": data_dir,
                "mode": mode,
                "marketplaces": marketplaces,
            }
            try:
                job = api_post("/jobs", json=payload)
            except requests.exceptions.RequestException as exc:
                st.error(f"Failed to submit job: {exc}")
            else:
                st.success(f"Job started: `{job['job_id']}`")

elif page == "Job Details":
    st.header("Job Details")

    job_id = st.text_input("Job ID")

    if job_id:
        try:
            job = api_get(f"/jobs/{job_id}")
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                st.error(f"Job `{job_id}` was not found.")
            else:
                st.error(f"Error: {exc}")
        except requests.exceptions.RequestException as exc:
            st.error(f"Failed to fetch job details: {exc}")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"Job ID: `{job['job_id']}`")
                st.write(f"Status: `{job.get('status', 'unknown')}`")
                st.write(f"Mode: `{job['mode']}`")
            with col2:
                st.write(f"Created: `{job['created_at']}`")
                if job.get("completed_at"):
                    st.write(f"Completed: `{job['completed_at']}`")

            st.write(f"Data directory: `{job['data_dir']}`")
            st.write(f"Marketplaces: `{', '.join(job.get('marketplaces', []))}`")

            if job.get("result_path"):
                st.info(f"Results stored under `{job['result_path']}`.")
            if job.get("error"):
                st.error(job["error"])

st.divider()
st.caption("Agentic Seller v0.1.0")
