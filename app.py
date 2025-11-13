import streamlit as st
import pandas as pd
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
import os
import json
import time
from datetime import datetime
import re

# --- Configuration ---
# Set these in Streamlit Cloud secrets: SERPER_API_KEY, GROQ_API_KEY

# --- Enhanced Output Schema ---
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

# Initialize Groq LLM properly for CrewAI
def get_groq_llm():
    """Initialize Groq LLM with LangChain compatibility"""
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY")),
        temperature=0.3
    )

# --- Enhanced Agents ---
research_specialist = Agent(
    role='Business Intelligence Research Specialist',
    goal="Conduct deep, targeted research to find specific business intelligence data with source URLs for all requested fields.",
    backstory="""Expert in business intelligence with 15+ years experience finding hard-to-locate corporate data.
    Specializes in identifying expansion news, IT infrastructure changes, and digital transformation initiatives.
    Known for meticulous source verification and comprehensive data collection.""",
    tools=[SerperDevTool()],
    verbose=True,
    allow_delegation=False,
    llm=get_groq_llm()
)

data_validator = Agent(
    role='Data Quality & Enrichment Specialist',
    goal="Review and enrich research data. Ensure ALL fields have meaningful data with proper sources and calculate accurate intent scoring.",
    backstory="""Data quality expert with background in business analytics and market intelligence.
    Excellent at identifying weak data points and finding additional sources to strengthen research.
    Specializes in intent signal detection and relevance analysis.""",
    tools=[SerperDevTool()],
    verbose=True,
    allow_delegation=False,
    llm=get_groq_llm()
)

formatter = Agent(
    role='Data Formatting & Schema Specialist',
    goal="Format validated research data into the exact JSON schema ensuring every field is populated with appropriate data and source citations.",
    backstory="""Technical data specialist with expertise in data formatting and schema compliance.
    Ensures all output meets specified standards and is ready for downstream processing.
    Meticulous about data structure and field completion.""",
    verbose=True,
    allow_delegation=False,
    llm=get_groq_llm()
)

# --- Enhanced Research Tasks ---
def create_research_tasks(company_name):
    """Create comprehensive research tasks"""
    
    research_task = Task(
        description=f"""
        CONDUCT COMPREHENSIVE RESEARCH FOR: {company_name}
        
        RESEARCH ALL THESE FIELDS WITH SOURCE LINKS:
        
        1. BASIC COMPANY INFO:
           - LinkedIn URL (find official company page)
           - Company Website URL (official domain)
           - Industry Category (primary business sector)
           - Employee Count (from LinkedIn or similar)
           - Headquarters Location (city, country)
           - Revenue Information (from ZoomInfo/Owler/Apollo or financial reports)
        
        2. CORE BUSINESS INTELLIGENCE (YOUR MAIN FOCUS):
           - Branch Network / Facilities Count (number of offices/warehouses/branches)
           - Expansion News Last 12 Months (new facilities, branches, geographic expansion)
           - Digital Transformation Initiatives (smart infrastructure, IT modernization programs)
           - IT Infrastructure Leadership Changes (new CIO/CTO/Head of Infrastructure appointments)
           - Existing Network Vendors / Tech Stack (Cisco, Juniper, Aruba, VMware, etc.)
           - Recent Wi-Fi Upgrade or LAN Tender Found (look for tender notices, upgrade announcements)
           - IoT / Automation / Edge Integration (smart factory, automation projects, edge computing)
           - Cloud Adoption / GCC Setup (AWS, Azure, Google Cloud adoption; Global Capability Centers)
           - Physical Infrastructure Signals (new data centers, office expansions, facility upgrades)
           - IT Infra Budget / Capex Allocation (IT spending, infrastructure investment plans)
        
        RESEARCH STRATEGY:
        - Use multiple search queries for each field
        - Look for recent information (2023-2025)
        - Prioritize official sources: company websites, LinkedIn, press releases
        - Include news articles, industry reports, tender portals
        - NEVER SKIP ANY FIELD - if data is unavailable, explain why and what was searched
        
        CRITICAL: Provide source URLs for every piece of information found.
        """,
        agent=research_specialist,
        expected_output="Comprehensive research notes with data for all fields and source URLs"
    )

    validation_task = Task(
        description=f"""
        VALIDATE AND ENRICH RESEARCH DATA FOR: {company_name}
        
        REVIEW THE RESEARCHER'S FINDINGS AND:
        1. Verify source credibility and data accuracy
        2. Cross-check important findings with additional searches
        3. Identify any missing or weak data points and find better sources
        4. Calculate Intent Scoring (1-10) based on:
           - Expansion activities found
           - IT infrastructure projects
           - Digital transformation initiatives
           - Leadership changes
           - Budget allocations
        5. Analyze "Why Relevant to Syntel" based on concrete business signals
        
        ENSURE DATA COMPLETION:
        - No field should be empty
        - All sources must be verifiable URLs
        - Intent scoring must be justified by specific findings
        
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
        
        Output must be valid JSON that can be parsed by the Pydantic model.
        """,
        agent=formatter,
        expected_output="Perfectly formatted JSON output matching the CompanyData schema",
        output_json=CompanyData
    )
    
    return [research_task, validation_task, formatting_task]

# --- Streamlit UI ---
st.set_page_config(
    page_title="Syntel Business Intelligence Agent", 
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Syntel Company Data AI Agent")
st.markdown("### Powered by CrewAI + Groq + Serper Search")

# Initialize session state
if 'research_history' not in st.session_state:
    st.session_state.research_history = []

# Input section
col1, col2 = st.columns([2, 1])
with col1:
    company_input = st.text_input("Enter the company name to research:", "Wipro")
with col2:
    st.write("")
    st.write("")
    research_button = st.button("🚀 Start Deep Research", type="primary")

if research_button:
    if not company_input:
        st.warning("Please enter a company name.")
    else:
        # Display research progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("AI Agents are conducting deep research... This may take 2-3 minutes."):
            try:
                # Update progress
                status_text.info("🔍 Phase 1/3: Initial research started...")
                progress_bar.progress(20)
                
                # Create tasks and crew
                tasks = create_research_tasks(company_input)
                project_crew = Crew(
                    agents=[research_specialist, data_validator, formatter],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=True
                )
                
                # Execute research
                status_text.info("🔍 Phase 2/3: Data validation and enrichment...")
                progress_bar.progress(50)
                
                result = project_crew.kickoff()
                
                status_text.info("🔍 Phase 3/3: Final formatting...")
                progress_bar.progress(80)
                
                # Get the result
                progress_bar.progress(100)
                status_text.success("✅ Research Complete!")
                
                # Display results
                st.success(f"✅ Comprehensive research completed for {company_input}")
                
                # Parse and display the result
                try:
                    # Try to extract JSON from the result
                    result_text = str(result)
                    
                    # Look for JSON pattern in the result
                    json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        data = json.loads(json_str)
                        
                        # Validate with Pydantic
                        validated_data = CompanyData(**data)
                        
                        # Store in session state
                        research_entry = {
                            "company": company_input,
                            "timestamp": datetime.now().isoformat(),
                            "data": validated_data.dict()
                        }
                        st.session_state.research_history.append(research_entry)
                        
                        # Create tabs for different views
                        tab1, tab2, tab3 = st.tabs(["📊 Data Table", "🔍 Detailed View", "📈 Analysis"])
                        
                        with tab1:
                            # Convert to DataFrame for nice display
                            display_data = []
                            for field, value in validated_data.dict().items():
                                display_data.append({
                                    "Field": field.replace("_", " ").title(),
                                    "Value": str(value)[:200] + "..." if len(str(value)) > 200 else str(value),
                                    "Full Value": value
                                })
                            
                            df = pd.DataFrame(display_data)
                            st.dataframe(df[["Field", "Value"]], use_container_width=True, hide_index=True)
                        
                        with tab2:
                            # Detailed view with source links
                            st.subheader("🔍 Detailed Research Results")
                            data_dict = validated_data.dict()
                            
                            categories = {
                                "🏢 Basic Company Info": [
                                    "linkedin_url", "company_website_url", "industry_category",
                                    "employee_count_linkedin", "headquarters_location", "revenue_source"
                                ],
                                "📈 Core Business Intelligence": [
                                    "branch_network_count", "expansion_news_12mo", "digital_transformation_initiatives",
                                    "it_leadership_change", "existing_network_vendors", "wifi_lan_tender_found",
                                    "iot_automation_edge_integration", "cloud_adoption_gcc_setup", 
                                    "physical_infrastructure_signals", "it_infra_budget_capex"
                                ],
                                "🎯 Analysis & Scoring": [
                                    "why_relevant_to_syntel", "intent_scoring"
                                ]
                            }
                            
                            for category, fields in categories.items():
                                with st.expander(category, expanded=True):
                                    for field in fields:
                                        if field in data_dict:
                                            col1, col2 = st.columns([3, 1])
                                            with col1:
                                                st.markdown(f"**{field.replace('_', ' ').title()}**")
                                                st.write(data_dict[field])
                                            with col2:
                                                # Check if value contains URL and make it clickable
                                                if isinstance(data_dict[field], str) and 'http' in data_dict[field]:
                                                    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', data_dict[field])
                                                    for url in urls[:2]:  # Show first 2 URLs
                                                        st.markdown(f'[🔗 Source]({url})')
                                            st.divider()
                        
                        with tab3:
                            # Analysis tab
                            st.subheader("📈 Business Intelligence Analysis")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Intent Score", f"{validated_data.intent_scoring}/10")
                            with col2:
                                # Calculate data completeness
                                filled_fields = sum(1 for value in validated_data.dict().values() if value and str(value).strip() and "not found" not in str(value).lower())
                                total_fields = len(validated_data.dict())
                                completeness = (filled_fields / total_fields) * 100
                                st.metric("Data Completeness", f"{completeness:.1f}%")
                            with col3:
                                st.metric("Research Date", datetime.now().strftime("%Y-%m-%d"))
                            
                            # Relevance analysis
                            st.subheader("🎯 Relevance to Syntel")
                            st.info(validated_data.why_relevant_to_syntel)
                            
                            # Download button
                            filename = f"{company_input.replace(' ', '_')}_data.json"
                            st.download_button(
                                label="📥 Download JSON Data",
                                data=json.dumps(validated_data.dict(), indent=2),
                                file_name=filename,
                                mime="application/json"
                            )
                    
                    else:
                        # If no JSON found, show raw result
                        st.warning("Could not parse structured data. Showing raw result:")
                        st.write(result)
                        
                except Exception as e:
                    st.error(f"Error parsing results: {str(e)}")
                    st.write("Raw result:")
                    st.write(result)
                    
            except Exception as e:
                st.error(f"Research failed: {str(e)}")
                st.markdown("""
                **Common Issues:**
                - Ensure GROQ_API_KEY and SERPER_API_KEY are set in Streamlit secrets
                - Check your API quotas
                - Try a different company name
                """)

# Research history
if st.session_state.research_history:
    st.sidebar.header("📚 Research History")
    for i, research in enumerate(reversed(st.session_state.research_history)):
        with st.sidebar.expander(f"{research['company']} - {research['timestamp'][:10]}", expanded=False):
            st.write(f"Intent Score: {research['data'].get('intent_scoring', 'N/A')}/10")
            if st.button(f"Load {research['company']}", key=f"load_{i}"):
                company_input = research['company']
                st.rerun()

# Instructions
with st.sidebar.expander("📖 Setup Instructions"):
    st.markdown("""
    **Required API Keys (set in Streamlit Cloud secrets):**
    - `GROQ_API_KEY`: Get from [groq.com](https://groq.com)
    - `SERPER_API_KEY`: Get from [serper.dev](https://serper.dev) - $50 free credit
    
    **How it works:**
    1. **Research Specialist** finds data with sources
    2. **Data Validator** verifies and enriches information  
    3. **Formatter** creates structured output
    4. **All 18 fields** are filled with source links
    """)
