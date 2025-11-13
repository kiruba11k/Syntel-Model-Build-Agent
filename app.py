import streamlit as st
import pandas as pd
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain_google_genai import ChatGoogleGenerativeAI 
# FIX: Changed import path from langchain.llms to langchain_community.llms
from langchain_community.llms import FakeListLLM 
from pydantic import BaseModel, Field
import os
import json
import time
from datetime import datetime
import re
import sys

# --- Configuration & Deployment Check ---
# You MUST set both keys in Streamlit secrets
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") # NEW REQUIRED KEY

if not SERPER_API_KEY:
    st.error("❌ ERROR: SERPER_API_KEY not found in Streamlit secrets. Please set it to enable search.")
    st.stop()

# --- Output Schema (No Change) ---
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

# FIX 2: Replaced OpenAI/Ollama with the Gemini API for deployment
def get_llm():
    if GEMINI_API_KEY:
        st.info("Using Gemini 2.5 Flash for live research.")
        
        # CrewAI/LiteLLM compatibility fix: 
        # The key should be passed to the LangChain wrapper.
        # The model name should be passed as standard.
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.2, 
            google_api_key=GEMINI_API_KEY # Explicitly pass the API key here
        )
    else:
        # Fallback to a mock LLM if key is missing
        st.warning("⚠️ WARNING: GEMINI_API_KEY not found. Using a mock LLM for demonstration (no actual research will occur).")
        # ... (rest of the FakeListLLM initialization remains the same)
        responses = [json.dumps(CompanyData(
            linkedin_url="Mock: linkedin.com/company/mockco", 
            company_website_url="Mock: mockco.com", 
            industry_category="Mock: Technology",
            employee_count_linkedin="Mock: 10,000+", 
            headquarters_location="Mock: Streamlit Cloud", 
            revenue_source="Mock: $1B (FakeListLLM)", 
            branch_network_count="Mock: 50+", 
            expansion_news_12mo="Mock: No real news - using FakeLLM.", 
            digital_transformation_initiatives="Mock: Placeholder data for schema compliance.", 
            it_leadership_change="Mock: CIO John Doe (Fake Source)", 
            existing_network_vendors="Mock: Cisco, Arista", 
            wifi_lan_tender_found="Mock: No", 
            iot_automation_edge_integration="Mock: Smart factory project mentioned.", 
            cloud_adoption_gcc_setup="Mock: AWS adoption in progress.", 
            physical_infrastructure_signals="Mock: New HQ opening in London.", 
            it_infra_budget_capex="Mock: $10M Capex (2025)",
            why_relevant_to_syntel="Mock: Strong expansion and clear digital initiatives point to major IT infra needs.",
            intent_scoring=8).dict())] * 10
        return FakeListLLM(responses=responses)

# Initialize LLM once
llm = get_llm()

# --- Agents ---
search_tool = SerperDevTool()

research_specialist = Agent(
    role='Business Intelligence Research Specialist',
    goal="Conduct deep, targeted research to find specific business intelligence data with source URLs for all requested fields.",
    backstory="Expert in business intelligence with 15+ years experience finding hard-to-locate corporate data. Specializes in identifying expansion news, IT infrastructure changes, and digital transformation initiatives. Known for meticulous source verification and comprehensive data collection.",
    tools=[search_tool],
    verbose=True,
    allow_delegation=False,
    llm=llm
)

data_validator = Agent(
    role='Data Quality & Enrichment Specialist',
    goal="Review and enrich research data. Ensure ALL fields have meaningful data with proper sources and calculate accurate intent scoring.",
    backstory="Data quality expert with background in business analytics and market intelligence. Excellent at identifying weak data points and finding additional sources to strengthen research. Specializes in intent signal detection and relevance analysis.",
    tools=[search_tool],
    verbose=True,
    allow_delegation=False,
    llm=llm
)

formatter = Agent(
    role='Data Formatting & Schema Specialist',
    goal="Format validated research data into the exact JSON schema ensuring every field is populated with appropriate data and source citations.",
    backstory="Technical data specialist with expertise in data formatting and schema compliance. Ensures all output meets specified standards and is ready for downstream processing. Meticulous about data structure and field completion.",
    verbose=True,
    allow_delegation=False,
    llm=llm,
    output_json=CompanyData
)

# --- Research Tasks (No Change) ---
def create_research_tasks(company_name):
    
    research_task = Task(
        description=f"""
        CONDUCT COMPREHENSIVE RESEARCH FOR: {company_name}
        ... (rest of the description is fine)
        CRITICAL: Provide source URLs for every piece of information found.
        """,
        agent=research_specialist,
        expected_output="Comprehensive research notes with data for all fields and source URLs"
    )

    validation_task = Task(
        description=f"""
        VALIDATE AND ENRICH RESEARCH DATA FOR: {company_name}
        ... (rest of the description is fine)
        FINAL OUTPUT: Validated, enriched dataset ready for formatting.
        """,
        agent=data_validator,
        expected_output="Validated dataset with quality scores and intent analysis"
    )

    formatting_task = Task(
        description=f"""
        FORMAT FINAL OUTPUT FOR: {company_name}
        
        Convert the validated research data into the exact JSON schema format.
        
        REQUIREMENTS:
        - All 18 fields must be populated
        - Source URLs must be included where specified
        - Data types must match schema requirements
        - Intent scoring (1-10 integer) must reflect research findings
        - "Why Relevant to Syntel" must be specific and actionable
        
        Output must be valid JSON that can be parsed by the Pydantic model. **ONLY OUTPUT THE JSON STRING. DO NOT ADD ANY MARKDOWN OR EXPLANATORY TEXT.**
        """,
        agent=formatter,
        expected_output="Perfectly formatted JSON output matching the CompanyData schema"
    )
    
    return [research_task, validation_task, formatting_task]

# --- Streamlit UI (Updated for clarity on the new key) ---
st.set_page_config(
    page_title="Syntel Business Intelligence Agent", 
    layout="wide"
)

st.title("Syntel Company Data AI Agent")
st.markdown("### Powered by CrewAI and Gemini/Serper Search")

# Initialize session state
if 'research_history' not in st.session_state:
    st.session_state.research_history = []

# Input section
col1, col2 = st.columns([2, 1])
with col1:
    company_input = st.text_input("Enter the company name to research:", "Wipro")
with col2:
    with st.form("research_form"):
        submitted = st.form_submit_button("Start Deep Research", type="primary")

if submitted:
    if not company_input:
        st.warning("Please enter a company name.")
    else:
        if isinstance(llm, FakeListLLM):
             st.warning("Research is running with **Mock Data** (FakeListLLM). Please provide a **`GEMINI_API_KEY`** in Streamlit secrets for live results.")
             time.sleep(1) 

        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("AI Agents are conducting deep research... This may take 2-3 minutes."):
            try:
                status_text.info("Phase 1/3: Initial research started...")
                progress_bar.progress(20)
                
                tasks = create_research_tasks(company_input)
                project_crew = Crew(
                    agents=[research_specialist, data_validator, formatter],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=1 
                )
                
                status_text.info("Phase 2/3: Data validation and enrichment...")
                progress_bar.progress(50)
                
                result = project_crew.kickoff()
                
                status_text.info("Phase 3/3: Final formatting...")
                progress_bar.progress(80)
                
                progress_bar.progress(100)
                status_text.success("Research Complete!")
                
                st.success(f"Comprehensive research completed for {company_input}")
                
                try:
                    result_text = str(result)
                    
                    json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        data = json.loads(json_str)
                        validated_data = CompanyData(**data)
                        
                        research_entry = {
                            "company": company_input,
                            "timestamp": datetime.now().isoformat(),
                            "data": validated_data.dict()
                        }
                        st.session_state.research_history.append(research_entry)
                        
                        tab1, tab2, tab3 = st.tabs(["Data Table", "Detailed View", "Analysis"])
                        
                        with tab1:
                            display_data = []
                            for field, value in validated_data.dict().items():
                                display_data.append({
                                    "Field": field.replace("_", " ").title(),
                                    "Value": str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
                                })
                            
                            df = pd.DataFrame(display_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        with tab2:
                            st.subheader("Detailed Research Results")
                            data_dict = validated_data.dict()
                            
                            categories = {
                                "Basic Company Info": [
                                    "linkedin_url", "company_website_url", "industry_category",
                                    "employee_count_linkedin", "headquarters_location", "revenue_source"
                                ],
                                "Core Business Intelligence": [
                                    "branch_network_count", "expansion_news_12mo", "digital_transformation_initiatives",
                                    "it_leadership_change", "existing_network_vendors", "wifi_lan_tender_found",
                                    "iot_automation_edge_integration", "cloud_adoption_gcc_setup", 
                                    "physical_infrastructure_signals", "it_infra_budget_capex"
                                ],
                                "Analysis & Scoring": [
                                    "why_relevant_to_syntel", "intent_scoring"
                                ]
                            }
                            
                            for category, fields in categories.items():
                                with st.expander(category, expanded=True):
                                    for field in fields:
                                        if field in data_dict:
                                            st.markdown(f"**{field.replace('_', ' ').title()}:** {data_dict[field]}")
                                            st.divider()
                        
                        with tab3:
                            st.subheader("Business Intelligence Analysis")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Intent Score", f"{validated_data.intent_scoring}/10")
                            with col2:
                                filled_fields = sum(1 for value in validated_data.dict().values() if value and str(value).strip() and "not found" not in str(value).lower() and "mock:" not in str(value).lower())
                                total_fields = len(validated_data.dict())
                                completeness = (filled_fields / total_fields) * 100
                                st.metric("Data Completeness", f"{completeness:.1f}%")
                            with col3:
                                st.metric("Research Date", datetime.now().strftime("%Y-%m-%d"))
                            
                            st.subheader("Relevance to Syntel")
                            st.info(validated_data.why_relevant_to_syntel)
                            
                            filename = f"{company_input.replace(' ', '_')}_data.json"
                            st.download_button(
                                label="Download JSON Data",
                                data=json.dumps(validated_data.dict(), indent=2),
                                file_name=filename,
                                mime="application/json"
                            )
                        
                    else:
                        st.warning("Could not parse structured data. Showing raw result:")
                        st.code(result, language='json')
                        
                except Exception as e:
                    st.error(f"Error parsing results: {str(e)}")
                    st.write("Raw result:")
                    st.code(result)
                    
            except Exception as e:
                st.error(f"Research failed: {str(e)}")
                st.markdown("""
                **Common Issues:**
                - Ensure **`SERPER_API_KEY`** is set in Streamlit secrets
                - Ensure **`GEMINI_API_KEY`** is set in Streamlit secrets (for live research)
                - Check your API quotas
                """)

# Research history
if st.session_state.research_history:
    st.sidebar.header("Research History")
    for i, research in enumerate(reversed(st.session_state.research_history)):
        with st.sidebar.expander(f"**{research['company']}** - {research['timestamp'][:10]}", expanded=False):
            st.write(f"Intent Score: {research['data'].get('intent_scoring', 'N/A')}/10")
            if st.button(f"Load {research['company']}", key=f"load_{i}"):
                st.session_state.company_input_from_history = research['company'] 
                st.rerun()

# Apply the history load logic
if 'company_input_from_history' in st.session_state:
    if st.session_state.company_input_from_history != company_input:
        company_input = st.session_state.company_input_from_history
        del st.session_state.company_input_from_history
        st.rerun()


# Instructions
with st.sidebar.expander("Setup Instructions ⚙️"):
    st.markdown("""
    This app uses **Gemini (free tier)** and **Serper Search** for research.

    **You MUST set both keys in your Streamlit Cloud secrets:**

    1.  **Search Tool:**
        - `SERPER_API_KEY`: Get from [serper.dev](https://serper.dev/) (provides $50 free credit).
    
    2.  **Language Model (LLM):**
        - **`GEMINI_API_KEY`**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey). This key provides a generous free tier for agent operations.

    **How it works (using Gemini 2.5 Flash):**
    1.  **Research Specialist** uses SerperDevTool to find data with sources.
    2.  **Data Validator** verifies, enriches information, and assigns an Intent Score.
    3.  **Formatter** creates the structured Pydantic JSON output.
    """)
