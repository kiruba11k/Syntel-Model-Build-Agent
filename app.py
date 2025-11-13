# enhanced_bi_agent.py
import streamlit as st
import pandas as pd
import requests
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedBIAgent:
    def __init__(self):
        self.ddgs = DDGS()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def multi_source_search(self, company_name, queries, max_results=5):
        """Search using multiple approaches with fallback"""
        all_results = []
        
        for query in queries:
            try:
                # Try DuckDuckGo first
                results = list(self.ddgs.text(
                    keywords=f"{company_name} {query}",
                    region="wt-wt",
                    safesearch="off",
                    max_results=max_results
                ))
                
                for result in results:
                    result['search_query'] = query
                    all_results.append(result)
                
                time.sleep(1)  # Be respectful to the service
                
            except Exception as e:
                logger.error(f"Search failed for {query}: {str(e)}")
                continue
        
        return all_results
    
    def extract_financial_signals(self, company_name):
        """Enhanced financial and infrastructure data extraction"""
        queries = [
            "IT budget 2024 2025",
            "capital expenditure capex infrastructure",
            "technology investment plan",
            "digital transformation budget",
            "IT infrastructure spending"
        ]
        
        results = self.multi_source_search(company_name, queries)
        
        financial_data = {
            "IT Infra Budget / Capex Allocation": {"value": "", "source": ""},
            "Physical Infrastructure Signals": {"value": "", "source": ""}
        }
        
        budget_patterns = [
            r'(\$?\d+(?:\.\d+)?\s*(?:million|billion|cr|crore|M|B))',
            r'budget.*?\$?\d+',
            r'capex.*?\$?\d+',
            r'invest.*?\$?\d+\s*(?:million|billion)'
        ]
        
        infrastructure_patterns = [
            r'data center|server room|facility expansion|new building|office expansion',
            r'cloud infrastructure|server upgrade|network upgrade',
            r'warehouse|logistics center|distribution facility'
        ]
        
        for result in results:
            content = f"{result.get('title', '')} {result.get('body', '')}".lower()
            url = result.get('href', '')
            
            # Extract budget information
            if not financial_data["IT Infra Budget / Capex Allocation"]["value"]:
                for pattern in budget_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        financial_data["IT Infra Budget / Capex Allocation"] = {
                            "value": f"Found financial signals: {', '.join(matches[:2])}",
                            "source": url
                        }
                        break
            
            # Extract infrastructure signals
            if not financial_data["Physical Infrastructure Signals"]["value"]:
                for pattern in infrastructure_patterns:
                    if re.search(pattern, content):
                        financial_data["Physical Infrastructure Signals"] = {
                            "value": f"Infrastructure development mentioned: {result.get('title', 'Infrastructure projects')}",
                            "source": url
                        }
                        break
        
        return financial_data
    
    def extract_technology_stack(self, company_name):
        """Enhanced technology stack research"""
        queries = [
            "technology stack IT infrastructure",
            "network vendors Cisco Juniper Aruba",
            "Wi-Fi upgrade LAN network",
            "cloud migration AWS Azure Google Cloud",
            "digital transformation tech stack"
        ]
        
        results = self.multi_source_search(company_name, queries)
        
        tech_data = {
            "Existing Network Vendors / Tech Stack": {"value": "", "source": ""},
            "Recent Wi-Fi Upgrade or LAN Tender Found": {"value": "", "source": ""},
            "Cloud Adoption / GCC Setup": {"value": "", "source": ""},
            "IoT / Automation / Edge Integration Mentioned": {"value": "", "source": ""}
        }
        
        vendor_keywords = ['cisco', 'juniper', 'aruba', 'hp', 'dell', 'vmware', 'microsoft']
        cloud_keywords = ['aws', 'azure', 'google cloud', 'gcp', 'cloud migration', 'saaS']
        iot_keywords = ['iot', 'internet of things', 'automation', 'edge computing', 'sensors']
        upgrade_keywords = ['upgrade', 'tender', 'RFP', 'request for proposal', 'modernization']
        
        for result in results:
            content = f"{result.get('title', '')} {result.get('body', '')}".lower()
            url = result.get('href', '')
            
            # Extract vendors
            if not tech_data["Existing Network Vendors / Tech Stack"]["value"]:
                found_vendors = [v for v in vendor_keywords if v in content]
                if found_vendors:
                    tech_data["Existing Network Vendors / Tech Stack"] = {
                        "value": f"Technologies mentioned: {', '.join(found_vendors)}",
                        "source": url
                    }
            
            # Extract cloud adoption
            if not tech_data["Cloud Adoption / GCC Setup"]["value"]:
                found_cloud = [c for c in cloud_keywords if c in content]
                if found_cloud:
                    tech_data["Cloud Adoption / GCC Setup"] = {
                        "value": f"Cloud services mentioned: {', '.join(found_cloud)}",
                        "source": url
                    }
            
            # Extract IoT/Automation
            if not tech_data["IoT / Automation / Edge Integration Mentioned"]["value"]:
                found_iot = [i for i in iot_keywords if i in content]
                if found_iot:
                    tech_data["IoT / Automation / Edge Integration Mentioned"] = {
                        "value": f"Emerging tech mentioned: {', '.join(found_iot)}",
                        "source": url
                    }
            
            # Extract upgrades
            if not tech_data["Recent Wi-Fi Upgrade or LAN Tender Found"]["value"]:
                found_upgrades = [u for u in upgrade_keywords if u in content and any(n in content for n in ['network', 'wi-fi', 'lan', 'it'])]
                if found_upgrades:
                    tech_data["Recent Wi-Fi Upgrade or LAN Tender Found"] = {
                        "value": f"Upgrade activity: {result.get('title', 'Network improvements')}",
                        "source": url
                    }
        
        return tech_data
    
    def research_company(self, company_name):
        """Comprehensive company research"""
        st.info(f"🔍 Starting enhanced research for {company_name}...")
        
        # Initialize all required fields
        results = {
            "Company Name": {"value": company_name, "source": "User Input"},
            "Core intent": {"value": "Business Intelligence Research", "source": "Default"},
            "Stage": {"value": "Active Research", "source": "Default"},
            "Branch Network / Facilities Count": {"value": "Researching...", "source": ""},
            "Expansion News (Last 12 Months)": {"value": "Researching...", "source": ""},
            "Digital Transformation Initiatives / Smart Infra Programs": {"value": "Researching...", "source": ""},
            "IT Infrastructure Leadership Change (CIO / CTO / Head Infra)": {"value": "Researching...", "source": ""},
            "Existing Network Vendors / Tech Stack": {"value": "Researching...", "source": ""},
            "Recent Wi-Fi Upgrade or LAN Tender Found": {"value": "Researching...", "source": ""},
            "IoT / Automation / Edge Integration Mentioned": {"value": "Researching...", "source": ""},
            "Cloud Adoption / GCC Setup": {"value": "Researching...", "source": ""},
            "Physical Infrastructure Signals": {"value": "Researching...", "source": ""},
            "IT Infra Budget / Capex Allocation": {"value": "Researching...", "source": ""},
            "Why Relevant to Syntel": {"value": "Researching...", "source": ""},
            "Intent scoring": {"value": "Researching...", "source": ""}
        }
        
        # Execute research phases
        research_phases = [
            ("💻 Technology Stack", self.extract_technology_stack),
            ("💰 Financial Analysis", self.extract_financial_signals)
        ]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (phase_name, research_func) in enumerate(research_phases):
            status_text.markdown(f'<div class="research-phase">Researching {phase_name}...</div>', unsafe_allow_html=True)
            try:
                phase_results = research_func(company_name)
                results.update(phase_results)
                progress_bar.progress((i + 1) / len(research_phases))
                time.sleep(2)
            except Exception as e:
                st.error(f"Error in {phase_name}: {str(e)}")
        
        # Calculate final scoring
        filled_fields = sum(1 for key in results if results[key]["value"] and "Researching" not in results[key]["value"])
        total_fields = len(results)
        completion_rate = (filled_fields / total_fields) * 100
        
        # Determine intent scoring
        if completion_rate > 70:
            intent_score = "High"
        elif completion_rate > 40:
            intent_score = "Medium"
        else:
            intent_score = "Low"
        
        results["Intent scoring"] = {"value": intent_score, "source": "Algorithm"}
        results["Why Relevant to Syntel"] = {
            "value": f"Found {filled_fields} of {total_fields} data points with {intent_score} intent signals",
            "source": "Analysis"
        }
        
        return results

# Streamlit UI Implementation
def main():
    st.set_page_config(page_title="Enhanced BI Research Agent", layout="wide")
    
    st.title("🏢 Enhanced Business Intelligence Agent")
    st.markdown("### Multi-Source Research with DuckDuckGo")
    
    # Initialize session state
    if 'enhanced_research' not in st.session_state:
        st.session_state.enhanced_research = []
    
    company_input = st.text_input("Enter Company Name:", placeholder="e.g., Infosys, Tata Consultancy")
    
    if st.button("🚀 Start Enhanced Research"):
        if company_input:
            agent = EnhancedBIAgent()
            
            with st.status("🔍 Conducting Multi-Source Research...", expanded=True) as status:
                results = agent.research_company(company_input)
                status.update(label="Research Complete!", state="complete")
            
            # Display results
            st.success(f"✅ Enhanced research completed for {company_input}")
            
            # Create results dataframe
            display_data = []
            for key, value_dict in results.items():
                display_data.append({
                    "Column": key,
                    "Value": value_dict.get("value", "Not found"),
                    "Source": value_dict.get("source", "Not available")
                })
            
            df = pd.DataFrame(display_data)
            
            # Show completion metrics
            col1, col2, col3 = st.columns(3)
            filled_count = sum(1 for row in display_data if row["Value"] and "Researching" not in row["Value"])
            
            with col1:
                st.metric("Total Fields", len(display_data))
            with col2:
                st.metric("Fields Filled", filled_count)
            with col3:
                st.metric("Completion Rate", f"{(filled_count/len(display_data))*100:.1f}%")
            
            # Display results in expandable sections
            for category in ["Technology", "Financial", "Infrastructure"]:
                with st.expander(f"{category} Intelligence", expanded=True):
                    category_data = [row for row in display_data if category.lower() in row["Column"].lower()]
                    if category_data:
                        for row in category_data:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**{row['Column']}**")
                                st.write(row['Value'])
                            with col2:
                                if row['Source'] and row['Source'] not in ['User Input', 'Default', 'Analysis', 'Algorithm']:
                                    st.markdown(f'[Source]({row["Source"]})')
                    else:
                        st.write(f"No {category} data found")
            
            # Store results
            st.session_state.enhanced_research.append({
                "company": company_input,
                "timestamp": datetime.now().isoformat(),
                "data": results
            })

if __name__ == "__main__":
    main()
