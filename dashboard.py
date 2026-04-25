"""Streamlit dashboard for Agentic Seller - job monitoring and review."""

import json
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(
    page_title="Agentic Seller Dashboard",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Agentic Seller Dashboard")
st.markdown("Monitor and review automated listing jobs")

# Get API URL from environment
API_URL = "http://backend:8000"  # Docker network access

# Sidebar for navigation
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Submit Job", "Job Details"],
)

if page == "Dashboard":
    st.header("Job Overview")

    try:
        response = requests.get(f"{API_URL}/jobs", timeout=5)
        response.raise_for_status()
        jobs_data = response.json()
        jobs = jobs_data.get("jobs", [])

        if not jobs:
            st.info("No jobs yet. Submit a new job to get started!")
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                pending = sum(1 for j in jobs if j.get("status") == "pending")
                st.metric("Pending", pending)
            with col2:
                running = sum(1 for j in jobs if j.get("status") == "running")
                st.metric("Running", running)
            with col3:
                completed = sum(1 for j in jobs if j.get("status") == "completed")
                st.metric("Completed", completed)
            with col4:
                failed = sum(1 for j in jobs if j.get("status") == "failed")
                st.metric("Failed", failed)

            st.subheader("Recent Jobs")
            for job in jobs[:10]:
                with st.expander(
                    f"🆔 {job['job_id'][:8]}... • {job['mode']} • {job.get('status', 'unknown')}"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Job ID:** {job['job_id']}")
                        st.write(f"**Status:** {job.get('status', 'unknown')}")
                        st.write(f"**Mode:** {job['mode']}")
                    with col2:
                        st.write(f"**Created:** {job['created_at']}")
                        if job.get("completed_at"):
                            st.write(f"**Completed:** {job['completed_at']}")
                    st.write(f"**Data Dir:** `{job['data_dir']}`")
                    st.write(f"**Marketplaces:** {', '.join(job.get('marketplaces', []))}")

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Failed to connect to backend: {e}")

elif page == "Submit Job":
    st.header("Submit New Job")

    with st.form("job_form"):
        data_dir = st.text_input(
            "Data Directory",
            value="/app/data/products",
            help="Path to folder containing product directories",
        )

        mode = st.radio(
            "Posting Mode",
            ["dry_run", "publish"],
            help="dry_run = no real submissions, publish = attempt live posting",
        )

        marketplaces = st.multiselect(
            "Target Marketplaces",
            ["olx", "facebook", "ceneo"],
            default=["olx", "facebook"],
        )

        submitted = st.form_submit_button("Submit Job", type="primary")

        if submitted:
            if not data_dir.strip():
                st.error("Data directory cannot be empty")
            elif not marketplaces:
                st.error("Please select at least one marketplace")
            else:
                try:
                    payload = {
                        "data_dir": data_dir,
                        "mode": mode,
                        "marketplaces": marketplaces,
                    }
                    response = requests.post(
                        f"{API_URL}/jobs",
                        json=payload,
                        timeout=5,
                    )
                    response.raise_for_status()
                    job = response.json()
                    st.success(
                        f"✅ Job submitted! Job ID: `{job['job_id']}`\n\nGo to Job Details to monitor."
                    )
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Failed to submit job: {e}")

elif page == "Job Details":
    st.header("Job Details")

    job_id = st.text_input("Enter Job ID to view details:")

    if job_id:
        try:
            response = requests.get(f"{API_URL}/jobs/{job_id}", timeout=5)
            response.raise_for_status()
            job = response.json()

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Job ID:** {job['job_id']}")
                st.write(f"**Status:** {job.get('status', 'unknown')}")
                st.write(f"**Mode:** {job['mode']}")
            with col2:
                st.write(f"**Created:** {job['created_at']}")
                if job.get("completed_at"):
                    st.write(f"**Completed:** {job['completed_at']}")

            st.write(f"**Data Directory:** `{job['data_dir']}`")
            st.write(f"**Marketplaces:** {', '.join(job.get('marketplaces', []))}")

            if job.get("result_path"):
                st.info(f"Results stored at: `{job['result_path']}`")

        except requests.exceptions.HTTPException as e:
            if e.response.status_code == 404:
                st.error(f"Job {job_id} not found")
            else:
                st.error(f"❌ Error: {e}")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Failed to fetch job details: {e}")

st.divider()
st.caption("Agentic Seller v0.1.0")
