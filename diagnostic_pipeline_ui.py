# diagnostic_pipeline_ui.py
import streamlit as st
import json
from enum import Enum
from requirements_loader import RequirementsLoader
from step3_clarifying_chat_ai import ClarifyingChatAIAgent
from step4_final_handoff import FinalHandoffManager, create_step4_ui
from step4_json_store import Step4JSONStore
 
# Page configuration
st.set_page_config(
    page_title="Diagnostic Pipeline",
    page_icon="📊",
    layout="wide"
)
 
# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        max-width: 1000px;
        padding: 2rem;
    }
    .header {
        color: #2c3e50;
        margin-bottom: 2rem;
    }
    .stSelectbox, .stButton {
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
 
# Enums for dropdown options
class ModelType(str, Enum):
    PD = "PD (Probability of Default)"
    LGD = "LGD (Loss Given Default)"
    EAD = "EAD (Exposure at Default)"
 
class Portfolio(str, Enum):
    RETAIL = "Retail"
    COMMERCIAL = "Commercial"
    WHOLESALE = "Wholesale"
 
class Purpose(str, Enum):
    IFRS9 = "IFRS 9"
    AIRB = "AIRB (Advanced Internal Ratings-Based)"
    ADJUDICATION = "Adjudication"
 
# Initialize session state variables
def init_session_state():
    """Initialize all required session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "requirements_loader" not in st.session_state:
        st.session_state.requirements_loader = RequirementsLoader()
    if "chat_ai_agent" not in st.session_state:
        st.session_state.chat_ai_agent = ClarifyingChatAIAgent()
    if "handoff_manager" not in st.session_state:
        st.session_state.handoff_manager = FinalHandoffManager()
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "diagnostic_started" not in st.session_state:
        st.session_state.diagnostic_started = False
    if "selected_config" not in st.session_state:
        st.session_state.selected_config = None
    if "show_step4" not in st.session_state:
        st.session_state.show_step4 = False
    if "last_lookup_result" not in st.session_state:
        st.session_state.last_lookup_result = None
 
init_session_state()
 
def perform_diagnostic_context_lookup(purpose: str, model_type: str) -> dict:
    """Load requirements for the selected configuration"""
    try:
        requirements_loader = st.session_state.requirements_loader
 
        if not requirements_loader.validate_configuration(purpose, model_type):
            return {
                "success": False,
                "error": f"No requirements defined for: {purpose} + {model_type}",
                "available_configurations": requirements_loader.get_available_configurations()
            }
 
        active_requirements = requirements_loader.get_active_requirements(purpose, model_type)
        st.session_state.active_requirements = active_requirements
 
        return {
            "success": True,
            "active_requirements": active_requirements,
            "lookup_key": requirements_loader._build_lookup_key(purpose, model_type)
        }
 
    except Exception as e:
        return {
            "success": False,
            "error": f"Error loading requirements: {str(e)}"
        }
 
# Sidebar configuration
with st.sidebar:
    st.title("Configuration")
    st.markdown("---")
 
    model_type = st.selectbox(
        "Model Type",
        [m.value for m in ModelType],
        index=0,
        help="Select the type of credit risk model"
    )
 
    portfolio = st.selectbox(
        "Portfolio",
        [p.value for p in Portfolio],
        index=0,
        help="Select the portfolio type"
    )
 
    purpose = st.selectbox(
        "Purpose",
        [p.value for p in Purpose],
        index=0,
        help="Select the purpose of the analysis"
    )
 
    run_analysis = st.button("Run Diagnostic", type="primary")
 
    if run_analysis:
        st.session_state.diagnostic_started = True
        st.session_state.selected_config = {
            "model_type": model_type,
            "portfolio": portfolio,
            "purpose": purpose,
        }
        st.session_state.show_step4 = False
 
# Main content area
st.title("Risk Diagnostic Pipeline")
st.markdown("---")
 
# Display selected configuration and run analysis
if run_analysis or st.session_state.get("diagnostic_started", False):
    if st.session_state.get("selected_config"):
        model_type = st.session_state.selected_config["model_type"]
        portfolio = st.session_state.selected_config["portfolio"]
        purpose = st.session_state.selected_config["purpose"]
 
    st.subheader("Selected Configuration:")
    col1, col2, col3 = st.columns([1.5, 1, 1])
    with col1:
        st.markdown("**Model Type**")
        st.markdown(f'<div style="font-size: 2.0rem; line-height: 1.2;">{model_type}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("**Portfolio**")
        st.markdown(f'<div style="font-size: 2.0rem; line-height: 1.2;">{portfolio}</div>', unsafe_allow_html=True)
    with col3:
        st.markdown("**Purpose**")
        st.markdown(f'<div style="font-size: 2.0rem; line-height: 1.2;">{purpose}</div>', unsafe_allow_html=True)
 
    # Load requirements when analysis is run
    if run_analysis:
        with st.spinner("Loading diagnostic requirements..."):
            clean_model_type = model_type.split(" ")[0] if " " in model_type else model_type
            clean_purpose = purpose.split(" ")[0] if " " in purpose else purpose
 
            lookup_result = perform_diagnostic_context_lookup(clean_purpose, clean_model_type)
 
            if lookup_result["success"]:
                st.success("Requirements loaded successfully!")
 
                # Initialize the chat agent with loaded requirements
                st.session_state.chat_ai_agent.initialize_session(
                    model_type=clean_model_type,
                    portfolio=portfolio,
                    purpose=clean_purpose,
                    active_requirements=lookup_result["active_requirements"]
                )
 
                # Generate first question
                import asyncio
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    st.session_state.current_question = loop.run_until_complete(
                        st.session_state.chat_ai_agent.generate_next_question()
                    )
                    loop.close()
                except Exception as e:
                    st.error(f"Error generating question: {e}")
                    st.session_state.current_question = None
 
                st.session_state.last_lookup_result = lookup_result
            else:
                st.session_state.last_lookup_result = lookup_result
 
    # Show clarifying chat if requirements loaded successfully
    lookup_result = st.session_state.get("last_lookup_result")
    
    if lookup_result and lookup_result.get("success"):
        st.markdown("---")
        st.subheader("Clarifying Chat")

        # Show completion status
        completion_status = st.session_state.chat_ai_agent.get_completion_status()
 
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mandatory Fields", f"{completion_status['mandatory_completed']}/{completion_status['mandatory_total']}")
        with col2:
            st.metric("Optional Fields", f"{completion_status['optional_completed']}/{completion_status['optional_total']}")
        with col3:
            status_emoji = "✅" if completion_status['all_mandatory_complete'] else "⏳"
            st.metric("Status", f"{status_emoji} {'Complete' if completion_status['all_mandatory_complete'] else 'In Progress'}")

        # Show current question or completion message
        if st.session_state.current_question:
            question = st.session_state.current_question

            st.markdown("### Missing Field Questionnaire")
            st.markdown(f"**{question.question}**")

            if getattr(question, "context", None):
                if str(question.context).strip():
                    st.markdown(f"**Context:** {question.context}")
            if getattr(question, "example", None):
                if str(question.example).strip():
                    st.markdown(f"**Example:** {question.example}")

            # Input field based on field type
            if question.field_type == 'boolean':
                user_response = st.radio(
                    "Your response:",
                    ["Yes", "No"],
                    key=f"response_{question.field_name}"
                )
            else:
                user_response = st.text_area(
                    "Your response:",
                    key=f"response_{question.field_name}",
                    placeholder="Enter your response here...",
                    help="Provide a detailed response based on the question above."
                )

            # Submit button
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Submit Response", type="primary"):
                    try:
                        if user_response and user_response.strip():
                            result = st.session_state.chat_ai_agent.process_user_response(
                                question.field_name,
                                user_response
                            )

                            if result['success']:
                                st.success(result['message'])

                                # Save response to draft JSON
                                try:
                                    current_json = st.session_state.chat_ai_agent.get_current_json()
                                    saved_file = st.session_state.chat_ai_agent.save_current_json()

                                    json_store = Step4JSONStore()
                                    completion_status = st.session_state.chat_ai_agent.get_completion_status()
                                    draft = json_store.upsert_field(
                                        header=current_json.get("header", {}),
                                        field=question.field_name,
                                        value=result.get("value"),
                                        completion_status=completion_status,
                                    )
                                except Exception as e:
                                    st.error(f"Error saving response: {str(e)}")
                                    st.exception(e)

                                # Generate next question
                                import asyncio
                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    next_question = loop.run_until_complete(
                                        st.session_state.chat_ai_agent.generate_next_question()
                                    )
                                    loop.close()

                                    if next_question is None:
                                        st.session_state.current_question = None
                                        st.success("All questions completed!")
                                    else:
                                        st.session_state.current_question = next_question
                                        st.info("Response recorded. Next question loaded.")
                                except Exception as e:
                                    st.error(f"Error generating next question: {e}")
                                    st.session_state.current_question = None
                            else:
                                st.error(result['message'])
                        else:
                            st.error("Please provide a response before submitting.")
                    except Exception as e:
                        st.error(f"Submission error: {str(e)}")
                        st.exception(e)
        else:
            # All questions completed
            completion_status = st.session_state.chat_ai_agent.get_completion_status()
            if not completion_status.get("all_complete", False):
                st.warning("No active question is loaded yet. Click below to retry loading the next question.")

                if st.button("Retry Loading Question", type="primary"):
                    import asyncio
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        st.session_state.current_question = loop.run_until_complete(
                            st.session_state.chat_ai_agent.generate_next_question()
                        )
                        loop.close()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating question: {e}")
                        st.session_state.current_question = None

            else:
                st.success("All clarifying questions completed!")

                collected_data = st.session_state.chat_ai_agent.get_collected_data()
                with st.expander("Collected Data Summary", expanded=False):
                    st.json(collected_data)

            # Proceed to Step 4 button
            collected_data = st.session_state.chat_ai_agent.get_collected_data()
            completion_status = collected_data.get("completion_status") or {}
            if completion_status.get("all_mandatory_complete", False):
                if st.button("Proceed to Step 4 - Final Handoff", type="primary"):
                    try:
                        json_store = Step4JSONStore()
                        for k, v in (collected_data.get("user_specs") or {}).items():
                            json_store.upsert_field(
                                header=collected_data.get("header", {}),
                                field=k,
                                value=v,
                                completion_status=completion_status,
                            )
                        draft = json_store.load()
                        saved_file = st.session_state.handoff_manager.save_final_json(draft)
                        st.success(f"Final JSON automatically saved: {saved_file}")
                    except Exception as e:
                        st.error(f"Error saving final JSON: {str(e)}")
 
                    st.session_state.show_step4 = True
                    st.rerun()
            else:
                st.warning("Mandatory fields are not complete yet. Please finish Step 3 before proceeding to Step 4.")
 
            # Field summary
            with st.expander("Field Status Summary"):
                field_summary = st.session_state.chat_ai_agent.get_field_summary()
 
                for field in field_summary:
                    status_emoji = {
                        "pending": "⏳",
                        "provided": "✅",
                        "clarified": "🔄"
                    }.get(field['status'], "❓")
 
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        st.write(f"{status_emoji} **{field['display_name']}**")
                    with col2:
                        st.write(f"{'Mandatory' if field['mandatory'] else 'Optional'}")
                    with col3:
                        st.write(field['status'])
                    with col4:
                        if field['value']:
                            st.write(f"`{field['value'][:50]}...`" if len(field['value']) > 50 else f"`{field['value']}`")
                        else:
                            st.write("—")
 
                if st.button("Reset All Fields"):
                    st.session_state.chat_ai_agent.reset_session()
                    st.session_state.current_question = None
                    st.rerun()
 
    elif lookup_result and not lookup_result.get("success"):
        st.error("Failed to load requirements")
        st.error(lookup_result["error"])
 
        if "available_configurations" in lookup_result:
            st.info("Available configurations:")
            st.json(lookup_result["available_configurations"])
else:
    st.markdown("""
    
    ### 
    # About This Tool
    This diagnostic pipeline helps analyze credit risk models by:
    - Validating model performance
    - Identifying potential issues
    - Generating comprehensive reports
    
    ### Next Steps
    1. Select your model type, portfolio, and purpose
    2. Click 'Run Diagnostic'
    3. Review the results and download reports
    """)
 
# Step 4 - Final Handoff
if st.session_state.get("show_step4", False):
    create_step4_ui(st.session_state.handoff_manager)
 