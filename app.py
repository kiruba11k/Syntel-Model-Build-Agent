# app.py
import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime
import re
from bs4 import BeautifulSoup
import os
from urllib.parse import quote
import itertools

# Page configuration
st.set_page_config(
    page_title="Business Intelligence AI Agent",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .source-link {
        font-size: 0.8rem;
        color: #666;
        word-break: break-all;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

class BusinessIntelligenceAgent:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def brave_search(self, query, api_key=None, count=10):
        """Perform search using Brave Search API"""
        if not api_key:
            return {"results": [], "error": "Brave API key required"}
        
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {"X-Subscription-Token": api_key}
            params = {"q": query, "count": count, "country": "us"}
            
            response = self.session.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            return {"results": [], "error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"results": [], "error": str(e)}
    
    def google_search_fallback(self, query):
        """Fallback search using Google (via public endpoint)"""
        try:
            url = f"https://www.google.com/search?q={quote(query)}"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            for g in soup.find_all('div', class_='g')[:5]:
                anchor = g.find('a')
                if anchor and anchor.get('href'):
                    title = g.find('h3')
                    snippet = g.find('span', class_='aCOpRe')
                    results.append({
                        'title': title.text if title else 'No title',
                        'url': anchor['href'],
                        'description': snippet.text if snippet else 'No description'
                    })
            return {"results": results}
        except Exception as e:
            return {"results": [], "error": str(e)}
    
    def extract_company_basic_info(self, company_name):
        """Extract basic company information"""
        sources = []
        
        # Try multiple search queries for basic info
        queries = [
            f"{company_name} official website",
            f"{company_name} LinkedIn",
            f"{company_name} headquarters location",
            f"{company_name} industry",
            f"{company_name} employee count"
        ]
        
        info = {
            "Company Website URL": {"value": "", "source": ""},
            "LinkedIn URL": {"value": "", "source": ""},
            "Headquarters (Location)": {"value": "", "source": ""},
            "Industry Category": {"value": "", "source": ""},
            "Employee Count (LinkedIn)": {"value": "", "source": ""}
        }
        
        for query in queries:
            result = self.brave_search(query, st.secrets.get("BRAVE_API_KEY", ""))
            if "web" in result and "results" in result["web"]:
                for item in result["web"]["results"][:3]:
                    url = item.get('url', '')
                    title = item.get('title', '').lower()
                    desc = item.get('description', '').lower()
                    
                    # Extract website
                    if not info["Company Website URL"]["value"] and any(x in title for x in ['official', 'website', 'home']):
                        info["Company Website URL"] = {"value": url, "source": url}
                    
                    # Extract LinkedIn
                    if not info["LinkedIn URL"]["value"] and 'linkedin.com' in url:
                        info["LinkedIn URL"] = {"value": url, "source": url}
                    
                    # Extract headquarters
                    if not info["Headquarters (Location)"]["value"] and any(x in desc for x in ['headquarters', 'head office', 'based in', 'located in']):
                        location_match = re.search(r'(headquarters|based).*?([A-Za-z\s,]+)', desc)
                        if location_match:
                            info["Headquarters (Location)"] = {"value": location_match.group(2).strip(), "source": url}
                    
                    # Extract industry
                    if not info["Industry Category"]["value"] and any(x in desc for x in ['industry', 'sector']):
                        industry_match = re.search(r'(industry|sector).*?([A-Za-z\s]+)', desc)
                        if industry_match:
                            info["Industry Category"] = {"value": industry_match.group(2).strip(), "source": url}
        
        return info
    
    def research_expansion_news(self, company_name):
        """Research expansion news and facilities count"""
        queries = [
            f"{company_name} expansion news 2024 2025",
            f"{company_name} new facilities branches",
            f"{company_name} branch network locations",
            f"{company_name} warehouse office expansion"
        ]
        
        expansion_data = {
            "Branch Network / Facilities Count": {"value": "", "source": ""},
            "Expansion News (Last 12 Months)": {"value": "", "source": ""}
        }
        
        for query in queries:
            result = self.brave_search(query, st.secrets.get("BRAVE_API_KEY", ""))
            if "web" in result and "results" in result["web"]:
                for item in result["web"]["results"][:5]:
                    url = item.get('url', '')
                    title = item.get('title', '')
                    desc = item.get('description', '')
                    
                    # Look for facility counts
                    if not expansion_data["Branch Network / Facilities Count"]["value"]:
                        count_matches = re.findall(r'(\d+)\s*(branches|facilities|locations|offices|warehouses)', desc.lower())
                        if count_matches:
                            expansion_data["Branch Network / Facilities Count"] = {
                                "value": f"{count_matches[0][0]} {count_matches[0][1]}",
                                "source": url
                            }
                    
                    # Look for expansion news
                    if not expansion_data["Expansion News (Last 12 Months)"]["value"]:
                        if any(x in desc.lower() for x in ['expand', 'new facility', 'new branch', 'opening', 'launch']):
                            expansion_data["Expansion News (Last 12 Months)"] = {
                                "value": f"{title} - {desc[:200]}...",
                                "source": url
                            }
        
        return expansion_data
    
    def research_digital_transformation(self, company_name):
        """Research digital transformation initiatives"""
        queries = [
            f"{company_name} digital transformation initiatives",
            f"{company_name} smart infrastructure programs",
            f"{company_name} IT modernization",
            f"{company_name} technology upgrade"
        ]
        
        digital_data = {
            "Digital Transformation Initiatives / Smart Infra Programs": {"value": "", "source": ""},
            "IoT / Automation / Edge Integration Mentioned": {"value": "", "source": ""},
            "Cloud Adoption / GCC Setup": {"value": "", "source": ""}
        }
        
        for query in queries:
            result = self.brave_search(query, st.secrets.get("BRAVE_API_KEY", ""))
            if "web" in result and "results" in result["web"]:
                for item in result["web"]["results"][:5]:
                    url = item.get('url', '')
                    desc = item.get('description', '').lower()
                    
                    # Digital transformation
                    if not digital_data["Digital Transformation Initiatives / Smart Infra Programs"]["value"]:
                        if any(x in desc for x in ['digital transformation', 'digital initiative', 'smart infrastructure']):
                            digital_data["Digital Transformation Initiatives / Smart Infra Programs"] = {
                                "value": item.get('description', 'Digital initiatives found'),
                                "source": url
                            }
                    
                    # IoT/Automation
                    if not digital_data["IoT / Automation / Edge Integration Mentioned"]["value"]:
                        if any(x in desc for x in ['iot', 'automation', 'edge computing', 'sensors']):
                            digital_data["IoT / Automation / Edge Integration Mentioned"] = {
                                "value": "Yes - " + item.get('description', 'IoT/Automation mentioned'),
                                "source": url
                            }
                    
                    # Cloud adoption
                    if not digital_data["Cloud Adoption / GCC Setup"]["value"]:
                        if any(x in desc for x in ['cloud adoption', 'gcc setup', 'aws', 'azure', 'google cloud']):
                            digital_data["Cloud Adoption / GCC Setup"] = {
                                "value": item.get('description', 'Cloud initiatives mentioned'),
                                "source": url
                            }
        
        return digital_data
    
    def research_technology_stack(self, company_name):
        """Research technology stack and IT leadership"""
        queries = [
            f"{company_name} IT infrastructure leadership CIO CTO",
            f"{company_name} technology stack vendors",
            f"{company_name} network infrastructure",
            f"{company_name} Wi-Fi LAN upgrade tender"
        ]
        
        tech_data = {
            "IT Infrastructure Leadership Change (CIO / CTO / Head Infra)": {"value": "", "source": ""},
            "Existing Network Vendors / Tech Stack": {"value": "", "source": ""},
            "Recent Wi-Fi Upgrade or LAN Tender Found": {"value": "", "source": ""}
        }
        
        for query in queries:
            result = self.brave_search(query, st.secrets.get("BRAVE_API_KEY", ""))
            if "web" in result and "results" in result["web"]:
                for item in result["web"]["results"][:5]:
                    url = item.get('url', '')
                    desc = item.get('description', '').lower()
                    
                    # Leadership changes
                    if not tech_data["IT Infrastructure Leadership Change (CIO / CTO / Head Infra)"]["value"]:
                        if any(x in desc for x in ['cio', 'cto', 'it director', 'technology head']):
                            tech_data["IT Infrastructure Leadership Change (CIO / CTO / Head Infra)"] = {
                                "value": item.get('description', 'IT leadership mentioned'),
                                "source": url
                            }
                    
                    # Technology stack
                    if not tech_data["Existing Network Vendors / Tech Stack"]["value"]:
                        vendors = []
                        vendor_keywords = ['cisco', 'juniper', 'aruba', 'hp', 'dell', 'vmware', 'microsoft', 'oracle']
                        for vendor in vendor_keywords:
                            if vendor in desc:
                                vendors.append(vendor)
                        if vendors:
                            tech_data["Existing Network Vendors / Tech Stack"] = {
                                "value": f"Technologies mentioned: {', '.join(vendors)}",
                                "source": url
                            }
                    
                    # Network upgrades
                    if not tech_data["Recent Wi-Fi Upgrade or LAN Tender Found"]["value"]:
                        if any(x in desc for x in ['wi-fi upgrade', 'lan upgrade', 'network tender', 'infrastructure upgrade']):
                            tech_data["Recent Wi-Fi Upgrade or LAN Tender Found"] = {
                                "value": item.get('description', 'Network upgrade mentioned'),
                                "source": url
                            }
        
        return tech_data
    
    def research_financial_infrastructure(self, company_name):
        """Research financial and physical infrastructure"""
        queries = [
            f"{company_name} IT infrastructure budget capex",
            f"{company_name} physical infrastructure",
            f"{company_name} data center facilities"
        ]
        
        financial_data = {
            "Physical Infrastructure Signals": {"value": "", "source": ""},
            "IT Infra Budget / Capex Allocation": {"value": "", "source": ""}
        }
        
        for query in queries:
            result = self.brave_search(query, st.secrets.get("BRAVE_API_KEY", ""))
            if "web" in result and "results" in result["web"]:
                for item in result["web"]["results"][:5]:
                    url = item.get('url', '')
                    desc = item.get('description', '').lower()
                    
                    # Physical infrastructure
                    if not financial_data["Physical Infrastructure Signals"]["value"]:
                        if any(x in desc for x in ['data center', 'server room', 'network infrastructure', 'physical infrastructure']):
                            financial_data["Physical Infrastructure Signals"] = {
                                "value": item.get('description', 'Physical infrastructure mentioned'),
                                "source": url
                            }
                    
                    # Budget information
                    if not financial_data["IT Infra Budget / Capex Allocation"]["value"]:
                        budget_matches = re.findall(r'(\$?\d+\.?\d*\s*(million|billion|cr|lakhs)?)\s*(budget|capex|investment)', desc)
                        if budget_matches:
                            financial_data["IT Infra Budget / Capex Allocation"] = {
                                "value": f"Budget mentioned: {budget_matches[0][0]} {budget_matches[0][1] or ''}",
                                "source": url
                            }
        
        return financial_data
    
    def comprehensive_research(self, company_name):
        """Perform comprehensive research on a company"""
        st.info(f"🔍 Starting comprehensive research for {company_name}...")
        
        # Initialize results structure
        results = {
            "Company Name": {"value": company_name, "source": "User Input"},
            "Core intent": {"value": "Research", "source": "Default"},
            "Stage": {"value": "Analysis", "source": "Default"}
        }
        
        # Research phases with progress
        research_phases = [
            ("Basic Company Info", self.extract_company_basic_info),
            ("Expansion News", self.research_expansion_news),
            ("Digital Transformation", self.research_digital_transformation),
            ("Technology Stack", self.research_technology_stack),
            ("Financial Infrastructure", self.research_financial_infrastructure)
        ]
        
        for phase_name, research_func in research_phases:
            with st.spinner(f"Researching {phase_name}..."):
                try:
                    phase_results = research_func(company_name)
                    results.update(phase_results)
                    time.sleep(1)  # Be respectful to APIs
                except Exception as e:
                    st.error(f"Error in {phase_name}: {str(e)}")
        
        # Calculate intent scoring based on findings
        relevance_signals = sum(1 for key in results if results[key]["value"] and "source" in results[key] and results[key]["source"])
        intent_score = "High" if relevance_signals > 8 else "Medium" if relevance_signals > 5 else "Low"
        
        results["Why Relevant to Syntel"] = {
            "value": f"Found {relevance_signals} relevant business intelligence signals including expansion, digital transformation, and infrastructure initiatives",
            "source": "Analysis"
        }
        
        results["Intent scoring"] = {
            "value": intent_score,
            "source": "Algorithm"
        }
        
        return results

# Initialize session state
if 'research_results' not in st.session_state:
    st.session_state.research_results = []
if 'agent' not in st.session_state:
    st.session_state.agent = BusinessIntelligenceAgent()

# Main application
st.markdown('<h1 class="main-header">🏢 Business Intelligence AI Research Agent</h1>', unsafe_allow_html=True)

# Sidebar configuration
st.sidebar.header("🔧 Configuration")
api_key = st.sidebar.text_input("Brave Search API Key", 
                               value=st.secrets.get("BRAVE_API_KEY", ""),
                               type="password",
                               help="Get free API key from https://brave.com/search/api/")

# Sample companies for quick start
sample_companies = ["YES Bank", "Federal Bank", "Snowman Logistics", "Infosys", "Tata Consultancy Services"]

# Main input section
col1, col2 = st.columns([2, 1])
with col1:
    company_input = st.text_input("🏢 Enter Company Name", placeholder="e.g., YES Bank, Infosys, etc.")
with col2:
    st.write("")
    st.write("")
    use_sample = st.checkbox("Use sample company")

if use_sample:
    selected_company = st.selectbox("Select sample company:", sample_companies)
    company_input = selected_company

research_button = st.button("🚀 Start Comprehensive Research", type="primary", use_container_width=True)

# Research results section
if research_button and company_input:
    if not api_key:
        st.error("🔑 Please enter your Brave Search API Key in the sidebar")
        st.info("💡 Get free API key from: https://brave.com/search/api/")
    else:
        # Perform research
        with st.status("🔍 Conducting Real-time Research...", expanded=True) as status:
            results = st.session_state.agent.comprehensive_research(company_input)
            status.update(label="Research Complete! ✅", state="complete", expanded=False)
        
        # Store results
        st.session_state.research_results.append({
            "timestamp": datetime.now().isoformat(),
            "company": company_input,
            "data": results
        })
        
        # Display results in a beautiful format
        st.success(f"✅ Research completed for {company_input}")
        
        # Create display dataframe
        display_data = []
        for key, value_dict in results.items():
            display_data.append({
                "Column": key,
                "Value": value_dict.get("value", "Not found"),
                "Source": value_dict.get("source", "Not available")
            })
        
        df_display = pd.DataFrame(display_data)
        
        # Show results in tabs
        tab1, tab2, tab3 = st.tabs(["📊 Summary View", "🔍 Detailed Results", "📈 Analysis"])
        
        with tab1:
            # Create a compact summary table
            summary_data = []
            for key, value_dict in results.items():
                if value_dict.get("value") and value_dict.get("value") not in ["", "Not found"]:
                    summary_data.append({
                        "Field": key,
                        "Information": str(value_dict["value"])[:100] + "..." if len(str(value_dict["value"])) > 100 else str(value_dict["value"]),
                        "Source": value_dict.get("source", "N/A")
                    })
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No substantial data found for this company.")
        
        with tab2:
            # Detailed view with source links
            for i, row in df_display.iterrows():
                if row["Value"] and row["Value"] not in ["", "Not found"]:
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{row['Column']}**")
                            st.write(row["Value"])
                        with col2:
                            if row["Source"] and row["Source"] not in ["User Input", "Default", "Analysis", "Algorithm"]:
                                st.markdown(f'<p class="source-link">Source: <a href="{row["Source"]}" target="_blank">🔗</a></p>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<p class="source-link">Source: {row["Source"]}</p>', unsafe_allow_html=True)
                        st.divider()
        
        with tab3:
            # Analysis metrics
            total_fields = len(results)
            filled_fields = sum(1 for key in results if results[key]["value"] and results[key]["value"] not in ["", "Not found"])
            completion_rate = (filled_fields / total_fields) * 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Fields", total_fields)
            with col2:
                st.metric("Fields Filled", filled_fields)
            with col3:
                st.metric("Completion Rate", f"{completion_rate:.1f}%")
            
            # Intent scoring
            st.subheader("🎯 Intent Analysis")
            intent_score = results.get("Intent scoring", {}).get("value", "Low")
            st.write(f"**Intent Score:** {intent_score}")
            st.write(f"**Relevance:** {results.get('Why Relevant to Syntel', {}).get('value', '')}")

# Research history
if st.session_state.research_results:
    st.sidebar.header("📚 Research History")
    for i, research in enumerate(reversed(st.session_state.research_results[-5:])):
        with st.sidebar.expander(f"{research['company']} - {research['timestamp'][:16]}"):
            filled_count = sum(1 for key in research['data'] if research['data'][key]["value"] and research['data'][key]["value"] not in ["", "Not found"])
            st.write(f"Fields filled: {filled_count}/{len(research['data'])}")
            st.write(f"Intent: {research['data'].get('Intent scoring', {}).get('value', 'N/A')}")
            if st.button("Load", key=f"load_{i}"):
                st.session_state.current_research = research

# Download functionality
if st.session_state.research_results:
    st.sidebar.header("💾 Export Data")
    if st.sidebar.button("Download All Research as CSV"):
        # Convert all research to CSV
        all_data = []
        for research in st.session_state.research_results:
            row = {"Company": research["company"], "Research Date": research["timestamp"]}
            for key, value_dict in research["data"].items():
                row[key] = value_dict.get("value", "")
                row[f"{key} Source"] = value_dict.get("source", "")
            all_data.append(row)
        
        df_export = pd.DataFrame(all_data)
        csv = df_export.to_csv(index=False)
        st.sidebar.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"business_intelligence_research_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Built with ❤️ using Streamlit, Brave Search API, and Python</p>
    <p>💡 <em>Note: This tool uses free APIs and may have rate limits. For production use, consider premium data sources.</em></p>
</div>
""", unsafe_allow_html=True)
