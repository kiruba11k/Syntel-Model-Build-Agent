import streamlit as st
import pandas as pd
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from pydantic import BaseModel, Field
import os
import json
import time
from datetime import datetime
import re

# --- Configuration ---
# Requires SERPER_API_KEY in Streamlit secrets

# --- Output Schema ---
class CompanyData(BaseModel):
    linkedin_url: str = Field(description="LinkedIn URL and source/confidence.")
    company_website_url: str = Field(description="Official company website URL and source/confidence.")
    industry_category: str = Field(description="Industry category and source.")
    employee_count_linkedin: str = Field(description="Employee count range and source.")
    headquarters_location: str = Field(description="Headquarters city, country, and source.")
    revenue_source: str = Field(description="Revenue data point and specific source (ZoomInfo/Owler/Apollo/News).")

    branch_network_count: str = Field(description="Number of branches/facilities mentioned online and source.")
    expansion_news_12mo: str = Field(description="Summary of expansion news in the last 12 months and source link.")
    digital_transformation_initiatives: str = Field(description="Details on smart infra or digital programs and source link.")
    it_leadership_change: str = Field(description="Name and title of new CIO/CTO/Head of Infra if changed recently and source link.")
    existing_network_vendors: str = Field(description="Mentioned network vendors or tech stack and source.")
    wifi_lan_tender_found: str = Field(description="Yes/No and source link if a tender was found.")
    iot_automation_edge_integration: str = Field(description="Details on IoT/Automation/Edge mentions and source link.")
    cloud_adoption_gcc_setup: str = Field(description="Details on Cloud Adoption or Global Capability Centers (GCC) and source link.")
    physical_infrastructure_signals: str = Field(description="Any physical infra signals (new office, factory etc) and source link.")
    it_infra_budget_capex: str = Field(description="IT Infra Budget or Capex allocation details and source.")

    why_relevant_to_syntel: str = Field(description="Why this company is a relevant lead for Syntel (based on all data).")
    intent_scoring: int = Field(description="Intent score 1-10 based on buying signals detected.")

# --- LLM (Optimized for Streamlit Cloud) ---
def get_llm():
    """Fallback fake LLM for Streamlit Cloud (no local model dependency)."""
    try:
        from langchain_community.llms import Ollama
        return Ollama(model="llama2")
    except Exception:
        from langchain.llms import FakeListLLM
        responses = ["Research data would appear here in production."]
        return FakeListLLM(responses=responses)

# --- Agents ---
research_specialist = Agent(
    role='Business Intelligence Research Specialist',
    goal="Find corporate and IT intelligence data with source URLs for all fields.",
    backstory="Expert in business intelligence, digital transformation tracking, and sourcing verifiable company data.",
    tools=[SerperDevTool()],
    verbose=True,
    allow_delegation=False,
    llm=get_llm()
)

data_validator = Agent(
    role='Data Quality & Enrichment Specialist',
    goal="Validate and enrich data. Ensure all fields have credible sources and assign accurate intent scores.",
    backstory="Data enrichment expert with focus on IT infrastructure signals and investment intent analysis.",
    tools=[SerperDevTool()],
    verbose=True,
    allow_delegation=False,
    llm=get_llm()
)

formatter = Agent(
    role='Data Formatting & Schema Specialist',
    goal="Convert research data into the defined JSON schema ensuring full compliance.",
    backstory="Technical data specialist ensuring complete structured JSON output for downstream analytics.",
    verbose=True,
    allow_delegation=False,
    llm=get_llm()
)

# --- Research Task Setup ---
def create_research_tasks(company_name):
    research_task = Task(
        description=f"""
        Conduct deep research for company: {company_name}

        Research all required fields:
        - LinkedIn URL, Company Website, Industry, Employee Count, HQ Location, Revenue
        - Expansion news (12 months), Digital Transformation, IT Leadership, Network Vendors
        - Wi-Fi/LAN tenders, IoT/Automation, Cloud/GCC adoption, Physical Infrastructure
        - IT Infra Budget, Intent signals, Relevance to Syntel

        Include credible source links (press releases, LinkedIn, official websites).
        """,
        agent=research_specialist,
        expected_output="Comprehensive research data with sources."
    )

    validation_task = Task(
        description=f"""
        Validate and enrich data for {company_name}.
        Ensure all fields are complete and credible, then assign intent score (1–10)
        based on IT signals and expansion activity.
        """,
        agent=data_validator,
        expected_output="Validated and enriched company intelligence dataset."
    )

    formatting_task = Task(
        description=f"""
        Format validated research for {company_name} into exact JSON schema.
        Ensure compliance with field names, datatypes, and completeness.
        """,
        agent=formatter,
        expected_output="Final JSON structured output matching CompanyData schema."
    )

    return [research_task, validation_task, formatting_task]

# --- Streamlit UI ---
st.set_page_config(page_title="Syntel Business Intelligence Agent", layout="wide")
st.title("🏢 Syntel Company Intelligence Agent")
st.markdown("AI-powered business data researcher using CrewAI and Serper Search")

if 'research_history' not in st.session_state:
    st.session_state.research_history = []

col1, col2 = st.columns([2, 1])
with col1:
    company_input = st.text_input("Enter a company name:", "Wipro")
with col2:
    research_button = st.button("🔍 Start Research", type="primary")

if research_button:
    if not company_input:
        st.warning("Please enter a company name.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        with st.spinner("AI Agents are conducting multi-stage research..."):
            try:
                status_text.info("Phase 1: Researching data...")
                progress_bar.progress(25)
                tasks = create_research_tasks(company_input)
                crew = Crew(
                    agents=[research_specialist, data_validator, formatter],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=True
                )
                status_text.info("Phase 2: Validating and formatting...")
                progress_bar.progress(65)
                result = crew.kickoff()

                status_text.info("Phase 3: Finalizing output...")
                progress_bar.progress(90)
                result_text = str(result)
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    data = json.loads(json_str)
                    validated_data = CompanyData(**data)

                    st.success(f"Research complete for **{company_input}** ✅")
                    progress_bar.progress(100)
                    status_text.success("All stages completed successfully!")

                    st.session_state.research_history.append({
                        "company": company_input,
                        "timestamp": datetime.now().isoformat(),
                        "data": validated_data.dict()
                    })

                    # Tabs for visualization
                    tab1, tab2, tab3 = st.tabs(["📋 Data Table", "🔎 Details", "📈 Analysis"])
                    with tab1:
                        df = pd.DataFrame([
                            {"Field": k.replace("_", " ").title(), "Value": v}
                            for k, v in validated_data.dict().items()
                        ])
                        st.dataframe(df, use_container_width=True, hide_index=True)

                    with tab2:
                        st.subheader("Detailed Insights")
                        for k, v in validated_data.dict().items():
                            st.markdown(f"**{k.replace('_', ' ').title()}**")
                            st.write(v)
                            st.divider()

                    with tab3:
                        st.metric("Intent Score", f"{validated_data.intent_scoring}/10")
                        filled_fields = sum(1 for v in validated_data.dict().values() if v)
                        total_fields = len(validated_data.dict())
                        st.metric("Data Completeness", f"{(filled_fields/total_fields)*100:.1f}%")
                        st.info(validated_data.why_relevant_to_syntel)
                        st.download_button(
                            label="⬇️ Download JSON",
                            data=json.dumps(validated_data.dict(), indent=2),
                            file_name=f"{company_input.replace(' ', '_')}_data.json",
                            mime="application/json"
                        )
                else:
                    st.warning("Could not parse JSON. Displaying raw output:")
                    st.write(result_text)
            except Exception as e:
                st.error(f"Error: {e}")
                st.markdown("""
                **Possible Fixes:**
                - Ensure `SERPER_API_KEY` is set in secrets
                - Check your API quota or internet access
                - Try a different company name
                """)

# Sidebar
if st.session_state.research_history:
    st.sidebar.header("📜 Research History")
    for i, entry in enumerate(reversed(st.session_state.research_history)):
        with st.sidebar.expander(f"{entry['company']} ({entry['timestamp'][:10]})", expanded=False):
            st.write(f"Intent Score: {entry['data'].get('intent_scoring', 'N/A')}")
            if st.button(f"Load {entry['company']}", key=f"load_{i}"):
                company_input = entry['company']
                st.rerun()

with st.sidebar.expander("⚙️ Setup Instructions"):
    st.markdown("""
    **Required API Keys:**
    - `SERPER_API_KEY` → from [serper.dev](https://serper.dev)

    **How it Works:**
    1. Research Specialist gathers data  
    2. Validator cross-checks & enriches it  
    3. Formatter converts to schema  
    4. Output is JSON-ready for analytics  
    """)
