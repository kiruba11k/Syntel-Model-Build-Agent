############################################################
# 🚀 Syntel Model Build Agent — Streamlit + CrewAI + Groq
# Author: Kirubakaran Periyasamy
# Description: Research workflow powered by Groq LLM
############################################################

import streamlit as st
import pandas as pd
import os
import time
import json
import re
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

############################################################
# ✅ Streamlit Setup
############################################################
st.set_page_config(page_title="Syntel Model Build Agent", layout="wide")
st.title("🤖 Syntel Model Build Agent – Powered by Groq")

st.markdown(
    """
    <style>
        .big-font {font-size:22px !important; font-weight:600;}
    </style>
    """,
    unsafe_allow_html=True,
)

############################################################
# ⚙️ LLM Setup (Groq)
############################################################
def get_llm():
    """Return a Groq-based LLM for use in CrewAI Agents."""
    try:
        llm = ChatGroq(
            model="mixtral-8x7b",  # Options: mixtral-8x7b, llama-3.1-70b
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        return llm
    except Exception as e:
        st.error(f"Groq LLM initialization failed: {e}")
        class DummyLLM:
            def __call__(self, prompt):
                return "⚠️ Groq initialization failed – using fallback response."
        return DummyLLM()

llm = get_llm()

############################################################
# 🧠 CrewAI Agent Definitions
############################################################
research_specialist = Agent(
    role="Business Intelligence Research Specialist",
    goal="Identify current and relevant business, financial, and tech insights from trusted sources.",
    backstory="You specialize in synthesizing research data and extracting valuable insights to assist decision-making teams.",
    allow_delegation=False,
    verbose=True,
    llm=llm
)

data_analyst = Agent(
    role="Data Analyst",
    goal="Analyze extracted data and provide trends, summaries, and statistics.",
    backstory="You are a data expert who understands patterns and derives insights from structured and unstructured data.",
    allow_delegation=False,
    verbose=True,
    llm=llm
)

report_writer = Agent(
    role="Report Writer",
    goal="Generate clear, concise, and professional research reports based on analyzed findings.",
    backstory="You are an expert communicator who converts analytical data into human-friendly summaries and presentations.",
    allow_delegation=False,
    verbose=True,
    llm=llm
)

############################################################
# 📋 User Input Section
############################################################
st.markdown("### 🧭 Enter Research Topic or Query")

topic = st.text_input("Enter a business / tech topic to research", placeholder="Example: AI adoption in Indian banking sector")

if topic:
    st.info(f"Analyzing topic: **{topic}**")
    with st.spinner("Fetching and analyzing data..."):
        time.sleep(1)

        ####################################################
        # 🧩 CrewAI Tasks
        ####################################################
        task1 = Task(
            description=f"Conduct in-depth online research about {topic} from credible sources (last 6 months).",
            expected_output="List of 10 key findings or insights with references.",
            agent=research_specialist,
        )

        task2 = Task(
            description=f"Analyze research findings for patterns, statistics, and regional insights on {topic}.",
            expected_output="Data-driven summary highlighting 3 major trends and supporting data.",
            agent=data_analyst,
        )

        task3 = Task(
            description=f"Write a professional and concise research report summarizing the findings and analysis about {topic}.",
            expected_output="Final formatted report suitable for business presentation or internal communication.",
            agent=report_writer,
        )

        ####################################################
        # ⚡ Crew Execution
        ####################################################
        crew = Crew(
            agents=[research_specialist, data_analyst, report_writer],
            tasks=[task1, task2, task3],
            process=Process.sequential,
            verbose=True,
        )

        try:
            result = crew.kickoff()
            st.success("✅ Research completed successfully!")
            st.markdown("### 📊 Final Report:")
            st.write(result)
        except Exception as e:
            st.error(f"❌ CrewAI execution failed: {e}")

else:
    st.info("👆 Please enter a topic above to start the Groq-powered research.")

############################################################
# 🧾 Footer
############################################################
st.markdown("---")
st.caption("Developed by Kirubakaran Periyasamy | Powered by CrewAI + Groq + Streamlit")
