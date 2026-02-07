# diagnostic_pipeline_ui.py
import streamlit as st
import json
from datetime import datetime
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
    if "chat_last_prompt_field" not in st.session_state:
        st.session_state.chat_last_prompt_field = None
    if "draft_saved" not in st.session_state:
        st.session_state.draft_saved = False
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
        st.session_state.chat_last_prompt_field = None
        st.session_state.draft_saved = False
 
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

                st.session_state.current_question = None
                st.session_state.chat_last_prompt_field = None
                st.session_state.draft_saved = False

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

        try:
            model_name = getattr(st.session_state.chat_ai_agent, 'model_name', None)
            llm_ready = False
            question_llm_ready = False
            chat_llm_ready = False
            try:
                llm_ready = bool(getattr(st.session_state.chat_ai_agent, '_llm_ready')())
            except Exception:
                llm_ready = False
            try:
                question_llm_ready = bool(getattr(st.session_state.chat_ai_agent, '_question_llm_ready')())
            except Exception:
                question_llm_ready = False
            try:
                chat_llm_ready = bool(getattr(st.session_state.chat_ai_agent, '_chat_llm_ready')())
            except Exception:
                chat_llm_ready = False
            if model_name:
                st.caption(
                    f"LLM model: {model_name} ({'ready' if llm_ready else 'not ready'}) | "
                    f"questions: {'ready' if question_llm_ready else 'fallback'} | "
                    f"chat: {'ready' if chat_llm_ready else 'fallback'}"
                )

            try:
                last_err = str(getattr(st.session_state.chat_ai_agent, 'last_ai_error', '') or '')
                if last_err and ('status_code: 402' in last_err or 'Insufficient credits' in last_err):
                    st.warning(
                        'LLM credits appear to be exhausted (402: Insufficient credits). '
                        'The app will fall back to deterministic prompts until credits are restored or the model/provider is changed.'
                    )
            except Exception:
                pass

            try:
                q_err = str(getattr(st.session_state.chat_ai_agent, 'last_question_ai_error', '') or '')
                c_err = str(getattr(st.session_state.chat_ai_agent, 'last_chat_ai_error', '') or '')
                if q_err and not question_llm_ready:
                    st.caption(f"Question LLM error: {q_err[:160]}")
                if c_err and not chat_llm_ready:
                    st.caption(f"Chat LLM error: {c_err[:160]}")
            except Exception:
                pass
        except Exception:
            pass

        chat_history = []
        try:
            if getattr(st.session_state.chat_ai_agent, "session", None) is not None:
                chat_history = st.session_state.chat_ai_agent.session.chat_history
        except Exception:
            chat_history = []

        try:
            next_question = st.session_state.chat_ai_agent.get_next_pending_question()
        except Exception:
            next_question = None

        if next_question is not None:
            try:
                source = 'fallback'
                is_llm = False
                if getattr(st.session_state.chat_ai_agent, 'session', None) is not None:
                    cache_llm = getattr(st.session_state.chat_ai_agent.session, 'question_cache_llm', {})
                    is_llm = bool(cache_llm.get(next_question.field_name, False))
                source = 'llm' if is_llm else 'fallback'
                st.caption(f"Question source: {source}")

                if not is_llm:
                    rej = str(getattr(st.session_state.chat_ai_agent, 'last_question_rejection', '') or '')
                    if rej.strip():
                        st.caption(f"Fallback reason: {rej}")
            except Exception:
                pass

            prompt_parts = [str(next_question.question or '').strip()]
            if getattr(next_question, "context", None) and str(next_question.context).strip():
                prompt_parts.append(f"Context: {next_question.context}")
            if getattr(next_question, "example", None) and str(next_question.example).strip():
                prompt_parts.append(f"Example: {next_question.example}")
            assistant_prompt = "\n\n".join([p for p in prompt_parts if p])

            last_msg = chat_history[-1] if chat_history else None
            already_seeded = bool(
                last_msg
                and last_msg.get('role') == 'assistant'
                and str(last_msg.get('field_name') or '') == str(next_question.field_name or '')
                and str(last_msg.get('content') or '').strip() == assistant_prompt.strip()
            )

            if not already_seeded:
                try:
                    if getattr(st.session_state.chat_ai_agent, "session", None) is not None:
                        st.session_state.chat_ai_agent.session.chat_history.append({
                            'role': 'assistant',
                            'field_name': next_question.field_name,
                            'content': assistant_prompt,
                            'timestamp': __import__('datetime').datetime.now().isoformat(),
                        })
                        chat_history = st.session_state.chat_ai_agent.session.chat_history
                except Exception:
                    pass

            st.session_state.chat_last_prompt_field = next_question.field_name

        for msg in chat_history:
            role = msg.get("role")
            content = str(msg.get("content", "") or "")
            if role in ("user", "assistant") and content.strip():
                with st.chat_message(role):
                    st.markdown(content)

        user_text = st.chat_input("Type your response...")
        if user_text:
            try:
                with st.chat_message("user"):
                    st.markdown(str(user_text))

                with st.chat_message("assistant"):
                    typing_placeholder = st.empty()
                    typing_placeholder.markdown("...")

                resp = st.session_state.chat_ai_agent.handle_user_message(user_text)
                if not resp.get("success"):
                    typing_placeholder.markdown(resp.get("message", "Failed to process message"))
                else:
                    st.rerun()
            except Exception as e:
                st.error(f"Submission error: {str(e)}")
                st.exception(e)

        completion_status = st.session_state.chat_ai_agent.get_completion_status()
        if completion_status.get("all_complete", False):
            st.success("All clarifying questions completed!")

        if completion_status.get("all_mandatory_complete", False) and not st.session_state.get("draft_saved", False):
            try:
                collected_data = st.session_state.chat_ai_agent.get_collected_data()
                ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"diagnostic_draft_{ts}.json"
                json_store = Step4JSONStore(filename=filename)
                json_store.save(
                    {
                        "header": collected_data.get("header", {}),
                        "user_specs": collected_data.get("user_specs", {}),
                    },
                    completion_status=completion_status,
                )
                st.session_state.draft_saved = True
            except Exception as e:
                st.error(f"Error saving draft: {str(e)}")

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
 