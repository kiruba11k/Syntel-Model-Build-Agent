import streamlit as st
import pandas as pd
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from pydantic import BaseModel, Field
import os
import json
from datetime import datetime
import re

# =========================================================
# CONFIGURATION
# =========================================================
# Required: GROQ_API_KEY and SERPER_API_KEY must be set in Streamlit secrets
# Example (in Streamlit Cloud secrets):
# GROQ_API_KEY = "your_groq_api_key"
# SERPER_API_KEY = "your_serper_api_key"

# =========================================================
# OUTPUT SCHEMA
# =========================================================
class CompanyData(BaseModel):
    # Basic Company Info
    linkedin_url: str = Field(description="LinkedIn URL and source/confidence.")
    company_website_url: str = Field(description="Official company website URL and source/confidence.")
    industry_category: str = Field(description="Industry category and source.")
    employee_count_linkedin: str = Field(description="Employee count range and source.")
    headquarters_location: str = Field(description="Headquarters city, country, and source.")
    revenue_source: str = Field(description="Revenue data point and specific source (ZoomInfo/Owler/Apollo/News).")

    # Core Research Fields
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

    # Analysis Fields
    why_relevant_to_syntel: str = Field(description="Why this company is a relevant lead for Syntel (based on all data).")
    intent_scoring: int = Field(description="Intent score 1-10 based on buying signals detected.")


# =========================================================
# AGENTS (GROQ BACKEND)
# =========================================================
research_specialist = Agent(
    role="Business Intelligence Research Specialist",
    goal="Conduct deep, targeted research to find specific business intelligence data with source URLs for all requested fields.",
    backstory="Expert in business intelligence with 15+ years experience finding hard-to-locate corporate data. Specializes in identifying expansion news, IT infrastructure changes, and digital transformation initiatives.",
    tools=[SerperDevTool()],
    verbose=True,
    allow_delegation=False,
    llm="groq/mixtral-8x7b"
)

data_validator = Agent(
    role="Data Quality & Enrichment Specialist",
    goal="Review and enrich research data. Ensure ALL fields have meaningful data with proper sources and calculate accurate intent scoring.",
    backstory="Data quality expert with background in business analytics and market intelligence. Excellent at identifying weak data points and finding additional sources to strengthen research.",
    tools=[SerperDevTool()],
    verbose=True,
    allow_delegation=False,
    llm="groq/mixtral-8x7b"
)

formatter = Agent(
    role="Data Formatting & Schema Specialist",
    goal="Format validated research data into the exact JSON schema ensuring every field is populated with appropriate data and source citations.",
    backstory="Technical data specialist with expertise in data formatting and schema compliance. Ensures all output meets specified standards and is ready for downstream processing.",
    verbose=True,
    allow_delegation=False,
    llm="groq/mixtral-8x7b"
)

# =========================================================
# RESEARCH TASKS
# =========================================================
def create_research_tasks(company_name):
    research_task = Task(
        description=f"""
        CONDUCT COMPREHENSIVE RESEARCH FOR: {company_name}

        RESEARCH ALL THESE FIELDS WITH SOURCE LINKS:

        1. BASIC COMPANY INFO:
           - LinkedIn URL
           - Company Website URL
           - Industry Category
           - Employee Count
           - Headquarters Location
           - Revenue Information

        2. CORE BUSINESS INTELLIGENCE:
           - Branch Network / Facilities Count
           - Expansion News (Last 12 Months)
           - Digital Transformation Initiatives
           - IT Leadership Changes
           - Existing Network Vendors / Tech Stack
           - Wi-Fi or LAN Tender Found
           - IoT / Automation / Edge Integration
           - Cloud Adoption / GCC Setup
           - Physical Infrastructure Signals
           - IT Infra Budget / Capex Allocation

        Strategy:
        - Use multiple search queries
        - Prioritize official sources (LinkedIn, company websites, press releases)
        - Use news portals (2023–2025)
        - Include verifiable URLs for each finding
        """,
        agent=research_specialist,
        expected_output="Comprehensive research notes with data for all fields and source URLs"
    )

    validation_task = Task(
        description=f"""
        VALIDATE AND ENRICH RESEARCH DATA FOR: {company_name}

        1. Verify source credibility and data accuracy
        2. Fill missing data
        3. Assign Intent Scoring (1–10)
        4. Summarize “Why Relevant to Syntel”

        Output: Validated, enriched dataset with intent scoring and relevance explanation.
        """,
        agent=data_validator,
        expected_output="Validated dataset with quality scores and intent analysis"
    )

    formatting_task = Task(
        description=f"""
        FORMAT FINAL OUTPUT FOR: {company_name}

        Convert the validated research data into strict JSON according to schema.
        Every field must be filled, properly typed, and include source citations.
        """,
        agent=formatter,
        expected_output="Final structured JSON output matching CompanyData schema"
    )

    return [research_task, validation_task, formatting_task]


# =========================================================
# STREAMLIT APP UI
# =========================================================
st.set_page_config(page_title="Syntel Business Intelligence Agent", layout="wide")
st.title("🏢 Syntel Company Data AI Agent")
st.markdown("### Powered by CrewAI + Groq Mixtral + Serper Search")

if 'research_history' not in st.session_state:
    st.session_state.research_history = []

col1, col2 = st.columns([2, 1])
with col1:
    company_input = st.text_input("Enter the company name to research:", "Wipro")
with col2:
    research_button = st.button("🚀 Start Deep Research", type="primary")

if research_button:
    if not company_input:
        st.warning("Please enter a company name.")
    else:
        progress = st.progress(0)
        status = st.empty()

        try:
            status.info("Phase 1/3: Researching...")
            progress.progress(20)
            tasks = create_research_tasks(company_input)
            project_crew = Crew(
                agents=[research_specialist, data_validator, formatter],
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )

            status.info("Phase 2/3: Validating and enriching...")
            progress.progress(60)
            result = project_crew.kickoff()

            status.info("Phase 3/3: Formatting output...")
            progress.progress(90)
            progress.progress(100)
            status.success("✅ Research Complete!")

            result_text = str(result)
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)

            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                validated = CompanyData(**data)

                st.session_state.research_history.append({
                    "company": company_input,
                    "timestamp": datetime.now().isoformat(),
                    "data": validated.dict()
                })

                tab1, tab2, tab3 = st.tabs(["📊 Data Table", "🧾 Detailed View", "💡 Analysis"])

                with tab1:
                    display_data = [
                        {"Field": k.replace("_", " ").title(), "Value": str(v)}
                        for k, v in validated.dict().items()
                    ]
                    st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)

                with tab2:
                    st.subheader("Detailed Research Results")
                    for k, v in validated.dict().items():
                        st.markdown(f"**{k.replace('_', ' ').title()}**: {v}")
                        st.divider()

                with tab3:
                    st.metric("Intent Score", f"{validated.intent_scoring}/10")
                    st.info(validated.why_relevant_to_syntel)
                    st.download_button(
                        "⬇️ Download JSON",
                        json.dumps(validated.dict(), indent=2),
                        file_name=f"{company_input}_data.json",
                        mime="application/json"
                    )

            else:
                st.warning("Could not parse structured JSON; showing raw output:")
                st.write(result)

        except Exception as e:
            st.error(f"⚠️ Research failed: {str(e)}")
            st.markdown("""
            **Possible Issues**
            - Missing `GROQ_API_KEY` or `SERPER_API_KEY` in Streamlit secrets
            - API quota exceeded
            - Try another company name
            """)

# =========================================================
# SIDEBAR HISTORY
# =========================================================
if st.session_state.research_history:
    st.sidebar.header("🕓 Research History")
    for i, item in enumerate(reversed(st.session_state.research_history)):
        with st.sidebar.expander(f"{item['company']} ({item['timestamp'][:10]})"):
            st.write(f"Intent Score: {item['data']['intent_scoring']}/10")
            if st.button(f"Reload {item['company']}", key=f"reload_{i}"):
                st.session_state.company_input = item['company']
                st.rerun()

st.sidebar.markdown("---")
st.sidebar.info("**Setup Required:**\n- Add `GROQ_API_KEY` and `SERPER_API_KEY` in Streamlit secrets.\n\n**Models Used:** Groq Mixtral-8x7B + CrewAI Agents.")
