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

# Use environment variables for API keys
os.environ["SERPER_API_KEY"] = st.secrets.get("SERPER_API_KEY", "")
os.environ["GROQ_API_KEY"] = st.secrets.get("GROQ_API_KEY", "")

# Simple schema
class CompanyData(BaseModel):
    company_name: str = Field(description="Company name")
    website: str = Field(description="Company website")
    industry: str = Field(description="Industry category")
    employee_count: str = Field(description="Employee count")
    headquarters: str = Field(description="Headquarters location")
    expansion_news: str = Field(description="Expansion news with source")
    digital_initiatives: str = Field(description="Digital transformation initiatives with source")
    intent_score: int = Field(description="Intent score 1-10")

# Initialize agents with simple configuration
research_agent = Agent(
    role='Research Specialist',
    goal='Find company information with sources',
    backstory='Expert researcher',
    tools=[SerperDevTool()],
    verbose=True
)

# Simple task
def create_task(company_name):
    return Task(
        description=f"Research {company_name} and find basic company information with source links.",
        agent=research_agent,
        expected_output="JSON data with company information"
    )

# Streamlit UI
st.title("Company Research Agent")
company_input = st.text_input("Enter company name:", "Wipro")

if st.button("Start Research"):
    if company_input:
        with st.spinner("Researching..."):
            try:
                task = create_task(company_input)
                crew = Crew(agents=[research_agent], tasks=[task], verbose=True)
                result = crew.kickoff()
                st.success("Research completed!")
                st.write(result)
            except Exception as e:
                st.error(f"Error: {str(e)}")
