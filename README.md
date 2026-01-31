1. The Objective
The objective is to create a user interface to a model developer agentic AI. The UI collects the context needed for another agent to use for model development. 

2. The "Diagnostic" Pipeline
Step 1: Base Configuration (The UI): Create a sidebar or header where the user selects the core parameters:
Model Type: (PD, LGD, EAD)
Portfolio: (Retail, Commercial, Wholesale)
Purpose: (IFRS 9, AIRB, Adjudication)
Step 2: Context Lookup: The system reads a local requirements_context.json. This file tells the agent which mandatory inputs are needed based on the selections in Step 1. 
[I will provide this file next week. For now use the simple json context provided below:
Json
{
  "AIRB_PD_Requirements": {
    "default_definition": {
      "mandatory": true,
      "description": "The specific criteria for default (e.g., 90 Days Past Due, bankruptcy, or unlikeliness to pay).",
      "example": "90 DPD + Materiality threshold"
    },
    "observation_period": {
      "mandatory": true,
      "description": "The historical look-back period used for calibration.",
      "example": "At least 5 years as per Basel standards"
    },
    "low_default_portfolio_flag": {
      "mandatory": false,
      "description": "Whether the portfolio has very few defaults, requiring alternative calibration techniques (e.g., Pluto-Tasche).",
      "example": "Yes/No"
    }
  },
  "IFRS9_LGD_Requirements": {
    "recovery_period": {
      "mandatory": true,
      "description": "The maximum time window allowed for recoveries to be considered in the LGD calculation.",
      "example": "24 months or 36 months"
    },
    "discount_rate": {
      "mandatory": true,
      "description": "The rate used to discount future recoveries back to the date of default (usually Effective Interest Rate).",
      "example": "EIR or WACC"
    },
    "forward_looking_scenarios": {
      "mandatory": true,
      "description": "The macroeconomic scenarios (Base, Upside, Downside) and their respective weightings.",
      "example": "Base (50%), Upside (20%), Downside (30%)"
    }
  }
}

]
Step 3: The Clarifying Chat: the agent then uses the parameters set by the user and the context file to ask further clarifying questions. If something is missing (e.g., "What is your definition of default?"), it asks the user to clarify.
Step 4: The Final Handoff: Once all fields are satisfied, the system compiles and saves a final .json file, ready for the modeling agent to execute.
For example:
Json
{
  "header": {
    "model_type": "PD",
    "portfolio": "Retail",
    "purpose": "AIRB"
  },
  "user_specs": {
    "default_definition": "90 DPD",
    "observation_period": "5 years",
    "additional_notes": "Exclude accounts closed within the last 6 months."
  }
}

Tech stack recommendations:
Let’s stay in python environment, unless there is a good reason to use other stacks:

Layer
Recommended Tool
Why for this project?
Frontend / UI
Streamlit
The industry standard for AI prototypes. It includes built-in st.chat_message components and handles reactive UI updates in pure Python.
Agent Orchestration
PydanticAI or LangGraph
PydanticAI is built for strict data validation (perfect for your JSON "Contract"). LangGraph is better if you need complex loops (self-correction).
Execution Engine
Python exec() or subprocess
For a demo, running generated code in a local subprocess is sufficient. It allows the agent to run a script, capture the error, and "try again."
Data Storage
Local JSON / SQLite
For the prototype phase, keep it simple. Save user specs as .json and model results in a local SQLite file.

