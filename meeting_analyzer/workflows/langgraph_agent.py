# meeting_analyzer/workflows/langgraph_agent.py

import os
import json
import subprocess
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from pathlib import Path

# LangChain/LangGraph imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


# --- 🔑 FIX 1: HARDCODED API KEY (Authentication Fix) ---
# WARNING: Replace this placeholder with your actual key if different.
GEMINI_KEY = "AIzaSyBapQCQo6a91AtsOjRwzDmqcQ4uYioLTZ0"
# --------------------------------------------------------


# --- CONFIGURATION and STATE ---

class AnalysisReport(BaseModel):
    """Schema for the final analysis output."""
    summary: str = Field(description="Summary of the key topics discussed.")
    action_items: List[str] = Field(description="List of action items and tasks assigned.")
    property_data: Dict[str, str] = Field(description="Extracted data about Site Name, Store Size, Signage, etc.")
    final_decision: str = Field(description="Final decision (approved, dropped/rejected, etc.).")


class WorkflowState(BaseModel):
    """
    FIX 2: The state of the agentic workflow.
    Only initial inputs are required. Generated fields have defaults.
    """
    # REQUIRED INPUTS
    google_transcript: str = Field(description="Content of the Google diarized transcript.")
    ppt_path: str = Field(description="Path to the property PPT file for context.")
    video_path: str = Field(description="Path to the source video file.")
    temp_dir: str = Field(description="Temporary directory for uploaded files.")

    # GENERATED FIELDS (Populated by workflow nodes)
    whisper_transcript: str = Field(default="", description="Content of the Whisper diarized transcript.")
    fused_transcript: str = Field(default="", description="The final, accurate, diarized transcript.")
    analysis_report: Dict[str, Any] = Field(default_factory=dict, description="The final structured analysis from Gemini.")
    error_message: str = Field(default="", description="Any error encountered during the workflow.")


# Initialize Gemini Model
# FIX 1 continued: Pass the key explicitly
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.0,
    max_tokens=4096,
    google_api_key=GEMINI_KEY
)
llm_vision = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.1,
    google_api_key=GEMINI_KEY
)


# --- HELPER FUNCTION ---

def load_file_content(file_path: str) -> str:
    """Loads text content from a file (supports .json or .txt)."""
    if file_path.lower().endswith(('.json', '.txt')):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    return ""


# --- NODES (Agent Functions) ---

def call_whisper_server(state: WorkflowState) -> Dict[str, Any]:
    """Executes the local Whisper CLI command via subprocess."""
    print("--- 🎙️ Executing Local Whisper CLI ---")
    video_path = state.video_path
    output_dir = state.temp_dir

    if not os.path.exists(video_path):
        error_msg = f"Video file not found at: {video_path}"
        return {"error_message": error_msg}

    command = [
        'whisper', str(video_path),
        '--model', 'base', '--language', 'en', '--task', 'transcribe',
        '--output_dir', str(output_dir), '--output_format', 'json'
    ]

    try:
        print(f"Running command: {' '.join(command)}")
        subprocess.run(command, check=True, capture_output=True, text=True)
        print("Whisper CLI execution successful.")

        video_filename = Path(video_path).stem
        json_output_path = Path(output_dir) / f"{video_filename}.json"

        if not json_output_path.exists():
            raise FileNotFoundError(f"Whisper output JSON not found at: {json_output_path}")

        with open(json_output_path, 'r', encoding='utf-8') as f:
            # Load the whisper JSON structure to ensure it's valid
            whisper_output_json = json.load(f)

        # Assuming whisper_output_json is a dict/json, store it as a string
        return {"whisper_transcript": json.dumps(whisper_output_json, indent=2)}

    except subprocess.CalledProcessError as e:
        error_msg = f"Whisper CLI failed. Ensure 'whisper' and 'ffmpeg' are in your PATH. Stderr: {e.stderr}"
        return {"error_message": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error during Whisper process: {e}"
        return {"error_message": error_msg}


def fuse_transcripts(state: WorkflowState) -> Dict[str, Any]:
    """Fuses two transcripts using Gemini for accuracy."""
    print("--- 🧠 Fusing Transcripts with Gemini ---")

    # If Whisper failed, skip fusion (optional logic, but good for robustness)
    if state.error_message or not state.whisper_transcript:
        return {"error_message": "Cannot fuse transcripts; Whisper transcription failed."}

    fusion_prompt = (
        "You are an expert transcript editor. Use the two transcripts to produce a single, detailed, "
        "accurate, and precise diarized transcript with corrected sentences and timestamps. "
        "Output strictly the complete final transcript text."
        "\n\n--- Google Transcript ---\n{google_transcript}"
        "\n\n--- Whisper Transcript ---\n{whisper_transcript}"
    )

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="You are a meticulous transcript fusion expert. Output only the final transcript."),
        HumanMessage(content=fusion_prompt.format(
            google_transcript=state.google_transcript,
            whisper_transcript=state.whisper_transcript
        ))
    ])

    try:
        fused_transcript_chain: Runnable = prompt | llm
        fused_transcript = fused_transcript_chain.invoke({}).content
        return {"fused_transcript": fused_transcript}
    except Exception as e:
        return {"error_message": f"Error during transcript fusion: {e}"}


def analyze_meeting(state: WorkflowState) -> Dict[str, Any]:
    """Passes the PPT file path and video path directly to Gemini for multimodal analysis."""
    print("--- 👁️ Analyzing Meeting with Gemini (Multimodal) ---")

    if state.error_message or not state.fused_transcript:
        return {"error_message": "Cannot analyze meeting; Transcript fusion failed."}

    analysis_prompt = """
    Analyze the attached VIDEO, the attached PPT file, and the provided fused transcript.
    The PPT file contains the visual presentation data. Use it to extract the required 'property_data'.

    Provide the analysis in a structured JSON format matching the AnalysisReport schema.

    INSTRUCTIONS:
    1. Summary of the key topics discussed.
    2. Action items, tasks assigned or decisions made.
    3. Property data (Site Name | Store Size | Signage | etc.). EXTRACT THIS DATA FROM THE ATTACHED PPT FILE.
    4. Final decision (approved, rejected, etc.).

    --- Final Accurate Transcript ---
    {fused_transcript}
    """

    # Contents list is passed to HumanMessage for multimodal input
    contents = [
        state.video_path,
        state.ppt_path,  # Passed directly as a file reference
        analysis_prompt.format(fused_transcript=state.fused_transcript)
    ]

    try:
        analysis_chain = (
                ChatPromptTemplate.from_messages([
                    SystemMessage(
                        content="You are an expert meeting analyst. You must analyze the VIDEO and the PPT file. Respond ONLY with a single JSON object that conforms to the provided schema."),
                    HumanMessage(content=contents)
                ])
                | llm_vision.with_structured_output(AnalysisReport)
        )

        analysis_result = analysis_chain.invoke({})
        return {"analysis_report": analysis_result.dict()}

    except Exception as e:
        return {"error_message": f"Error during meeting analysis: {e}"}


# --- GRAPH DEFINITION ---

def define_workflow() -> StateGraph:
    """Defines and compiles the LangGraph StateGraph."""

    workflow = StateGraph(WorkflowState)
    workflow.add_node("whisper_call", call_whisper_server)
    workflow.add_node("transcript_fusion", fuse_transcripts)
    workflow.add_node("meeting_analysis", analyze_meeting)

    def check_for_error(state: WorkflowState):
        # LangGraph conditional edge function to check for errors
        return "end_with_error" if state.error_message else "continue"

    # Define the flow
    workflow.set_entry_point("whisper_call")

    workflow.add_conditional_edges("whisper_call", check_for_error,
                                   {"continue": "transcript_fusion", "end_with_error": END})
    workflow.add_conditional_edges("transcript_fusion", check_for_error,
                                   {"continue": "meeting_analysis", "end_with_error": END})
    workflow.add_edge("meeting_analysis", END)

    return workflow.compile()