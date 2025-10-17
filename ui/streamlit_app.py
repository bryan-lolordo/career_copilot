"""
Streamlit UI for Career Copilot
"""
import streamlit as st
from services.resume_parser import parse_resume
from services.job_api import search_jobs

st.title("Career Copilot: Job Search Assistant")

uploaded_file = st.file_uploader("Upload your résumé (PDF or DOCX)")
query = st.text_input("Job search query", "Software Engineer")
location = st.text_input("Location (optional)")

if uploaded_file:
    resume_data = parse_resume(uploaded_file.name)
    st.write("Résumé parsed:", resume_data)
    if st.button("Search Jobs"):
        results = search_jobs(query, location)
        st.write("## Job Results")
        for job in results["results"]:
            st.markdown(f"**{job['title']}** at {job['company']}  ")
            st.markdown(f"Location: {job['location']}")
            st.markdown(f"[Apply Here]({job['url']})")
            st.markdown("---")
