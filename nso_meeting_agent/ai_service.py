import json
import os
import requests
import time
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# Use the API key provided by the user
API_KEY = "AIzaSyCxTCYQO7s23L33kC4Io4G-i1p1ytD-OiI"
MODEL_TEXT = "gemini-2.5-flash-preview-05-20"
API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_TEXT}:generateContent?key={API_KEY}"


def _call_llm_with_prompt(prompt, max_retries=5, initial_delay=1):
    """
    Makes a POST request to the Gemini API with exponential backoff for retries.
    It expects the LLM to return a JSON object.
    """
    headers = {
        'Content-Type': 'application/json'
    }

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    delay = initial_delay
    for i in range(max_retries):
        try:
            response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(payload))
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            raw_response = response.json()

            if 'candidates' not in raw_response or not raw_response['candidates']:
                print("Error: The Gemini API response does not contain a 'candidates' field.")
                print(f"Raw LLM response: {raw_response}")
                if 'promptFeedback' in raw_response and 'blockReason' in raw_response['promptFeedback']:
                    block_reason = raw_response['promptFeedback']['blockReason']
                    print(f"The request was blocked by the safety filter. Reason: {block_reason}")
                return {"error": "API response blocked or malformed."}

            text_content = raw_response['candidates'][0]['content']['parts'][0]['text']

            try:
                return json.loads(text_content)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON from LLM response: {e}")
                print(f"Raw LLM text content: {text_content}")
                return {"error": "Invalid JSON format from LLM."}

        except requests.exceptions.RequestException as e:
            if i < max_retries - 1:
                print(f"Attempt {i + 1} failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"All {max_retries} attempts failed. Error: {e}")
                return {"error": "Maximum retries exceeded or unexpected error."}


# Define the state of our agent's workflow. This is how data is passed between nodes.
class MeetingState(TypedDict):
    """Represents the state of our graph."""
    transcript: str
    ppt_content: str
    video_visuals: str
    combined_data: str
    key_points: list
    action_items: list
    summary: str


### AGENTIC TOOLS (as LangGraph Nodes) ###

def transcribe_audio_from_video(state: MeetingState):
    """TOOL: Simulates audio transcription and updates the state."""
    print("Executing LangGraph node: Transcribe Audio...")
    video_file = state.get("video_file", "unknown_video.mp4")
    mock_prompt = f"You are a mock transcription service. Generate a plausible, detailed meeting transcript for a video file named '{video_file}'. Include multiple speakers discussing a marketing campaign, project deadlines, and action items."
    transcript_text = _call_llm_with_prompt(mock_prompt)
    state['transcript'] = transcript_text.get('text', "")
    return state


def extract_text_from_ppt(state: MeetingState):
    """TOOL: Simulates text extraction from a PPT and updates the state."""
    print("Executing LangGraph node: Extract Text from PPT...")
    ppt_file = state.get("ppt_file", "unknown_ppt.pptx")
    mock_prompt = f"You are a mock PPT text extraction service. Generate plausible, detailed text content from a presentation file named '{ppt_file}'. Include a title slide about 'Q3 Marketing Campaign Review', a slide with a bulleted list of 'Key Metrics' (with numbers for lead gen and conversions), and a 'Next Steps' slide."
    ppt_text = _call_llm_with_prompt(mock_prompt)
    state['ppt_content'] = ppt_text.get('text', "")
    return state


def analyze_visuals_from_video(state: MeetingState):
    """TOOL: Simulates visual analysis and updates the state."""
    print("Executing LangGraph node: Analyze Video Visuals...")
    video_file = state.get("video_file", "unknown_video.mp4")
    mock_prompt = f"You are a mock video analysis service. Analyze a video file named '{video_file}' and describe the key visuals that would be relevant to a meeting summary. Mention any whiteboard notes, shared charts, or other visual aids."
    visual_text = _call_llm_with_prompt(mock_prompt)
    state['video_visuals'] = visual_text.get('text', "")
    return state


def combine_data(state: MeetingState):
    """Helper node to combine all processed data into a single string."""
    print("Executing LangGraph node: Combining Data...")
    state['combined_data'] = (
        f"Transcript:\n{state.get('transcript', '')}\n\n"
        f"PPT Content:\n{state.get('ppt_content', '')}\n\n"
        f"Video Visuals:\n{state.get('video_visuals', '')}"
    )
    return state


def identify_key_points(state: MeetingState):
    """AGENTIC TOOL: Uses the LLM to identify key points and updates the state."""
    print("Executing LangGraph node: Identifying Key Points...")
    combined_data = state['combined_data']
    prompt = f"""
    You are an expert at analyzing meeting data from multiple sources.
    Your task is to analyze the following combined meeting data and extract the most important key points.
    Return your response as a JSON object with the following structure:
    {{
        "key_points": [
            "A concise key point from the meeting."
        ]
    }}
    Combined Meeting Data:
    {combined_data}
    """
    result = _call_llm_with_prompt(prompt)
    state['key_points'] = result.get('key_points', [])
    return state


def extract_action_items(state: MeetingState):
    """AGENTIC TOOL: Uses the LLM to extract action items and updates the state."""
    print("Executing LangGraph node: Extracting Action Items...")
    combined_data = state['combined_data']
    prompt = f"""
    You are an expert at identifying action items from meeting data.
    Your task is to analyze the following combined meeting data and extract all action items.
    For each action item, identify the person responsible for the task.
    Return your response as a JSON object with the following structure:
    {{
        "action_items": [
            {{"person": "The person responsible", "task": "A clear description of the task"}}
        ]
    }}
    Combined Meeting Data:
    {combined_data}
    """
    result = _call_llm_with_prompt(prompt)
    state['action_items'] = result.get('action_items', [])
    return state


def synthesize_final_summary(state: MeetingState):
    """AGENTIC TOOL: Uses the LLM to synthesize the final summary and updates the state."""
    print("Executing LangGraph node: Synthesizing Final Summary...")
    combined_data = state['combined_data']
    key_points = state['key_points']
    action_items = state['action_items']
    prompt = f"""
    You are an expert summarizer. Your task is to synthesize a final, coherent summary of a meeting based on all its data (transcript, video, slides), key points, and action items.
    The summary should be a single, well-written paragraph that captures the essence of the meeting.
    Return your response as a JSON object with the following structure:
    {{
        "summary": "The final summary of the meeting."
    }}
    Meeting Details:
    Combined Meeting Data: {combined_data}
    Key Points: {json.dumps(key_points)}
    Action Items: {json.dumps(action_items)}
    """
    result = _call_llm_with_prompt(prompt)
    state['summary'] = result.get('summary', "N/A")
    return state


### AGENTIC ORCHESTRATOR (LangGraph Graph) ###

def main_langgraph_workflow(video_file, ppt_file):
    """
    The main workflow function that runs the LangGraph agent.
    """
    print("Starting LangGraph multi-modal agentic workflow...")

    # Define the graph
    workflow = StateGraph(MeetingState)

    # Add the nodes (our tools)
    workflow.add_node("transcribe_audio", transcribe_audio_from_video)
    workflow.add_node("extract_ppt_text", extract_text_from_ppt)
    workflow.add_node("analyze_video_visuals", analyze_visuals_from_video)
    workflow.add_node("combine_data", combine_data)
    workflow.add_node("identify_key_points", identify_key_points)
    workflow.add_node("extract_action_items", extract_action_items)
    workflow.add_node("synthesize_summary", synthesize_final_summary)

    # Define the graph's edges (the flow of execution)
    workflow.add_edge(START, "transcribe_audio")
    workflow.add_edge("transcribe_audio", "extract_ppt_text")
    workflow.add_edge("extract_ppt_text", "analyze_video_visuals")
    workflow.add_edge("analyze_video_visuals", "combine_data")
    workflow.add_edge("combine_data", "identify_key_points")
    workflow.add_edge("identify_key_points", "extract_action_items")
    workflow.add_edge("extract_action_items", "synthesize_summary")
    workflow.add_edge("synthesize_summary", END)

    # Compile the graph
    app = workflow.compile()

    # Run the graph
    final_state = app.invoke({"video_file": video_file, "ppt_file": ppt_file})

    print("LangGraph workflow completed.")
    return {
        "summary": final_state.get("summary", "N/A"),
        "key_points": final_state.get("key_points", []),
        "action_items": final_state.get("action_items", []),
    }
