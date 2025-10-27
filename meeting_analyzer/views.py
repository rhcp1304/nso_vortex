# meeting_analyzer/views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.conf import settings
# Import the workflow components from the local modules
from .workflows.langgraph_agent import define_workflow, WorkflowState, load_file_content
from .workflows.report_generator import generate_pdf_report
from .models import AnalysisTask
import os
import uuid
import shutil


def analysis_ui(request):
    """Renders the simple UI for file uploads."""
    # Ensure you have a 'templates' directory inside 'meeting_analyzer'
    return render(request, 'meeting_analyzer/analysis_ui.html')


@csrf_exempt
def start_analysis(request):
    """
    Handles file upload, saves files, starts LangGraph analysis, and returns the result.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

    task = None
    temp_dir = None

    # 1. Handle File Upload and Save
    try:
        # Use a model instance to save the files from the request
        task = AnalysisTask(
            ppt_file=request.FILES['ppt_file'],
            video_file=request.FILES['video_file'],
            transcript_file=request.FILES['transcript_file'],
        )
        task.save()

        # Get absolute paths of the uploaded files (these are in MEDIA_ROOT/uploads/)
        ppt_path = task.ppt_file.path
        video_path = task.video_file.path
        google_transcript_path = task.transcript_file.path

    except Exception as e:
        # Cleanup model record if upload failed
        if task: task.delete()
        return JsonResponse({"error": f"File upload failed. Ensure all three files are submitted: {e}"}, status=400)

    # --- SETUP: Temporary Directory for Whisper Output ---
    run_uuid = str(uuid.uuid4())
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'analysis_temp', run_uuid)
    os.makedirs(temp_dir, exist_ok=True)

    # --- INITIALIZE STATE ---
    try:
        initial_state = WorkflowState(
            # Load transcript content as text (supports .txt or .json)
            google_transcript=load_file_content(google_transcript_path),
            # Pass file paths directly to the workflow
            ppt_path=ppt_path,
            video_path=video_path,
            temp_dir=temp_dir,
        )

        if not initial_state.google_transcript:
            raise ValueError("Failed to load Google transcript content. Is the uploaded file empty or unreadable?")

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        task.delete()  # Cleanup uploaded files
        return JsonResponse({"error": f"Initialization failed: {e}"}, status=400)

    # --- RUN THE LANGGRAPH WORKFLOW ---
    try:
        app = define_workflow()

        print(f"Starting analysis for run {run_uuid}...")
        final_state_dict = app.invoke(initial_state.dict())
        final_state = WorkflowState(**final_state_dict)

        if final_state.error_message:
            return JsonResponse({"status": "failed", "error": final_state.error_message}, status=500)

        # --- GENERATE FINAL REPORT ---
        report_filename = f"analysis_{run_uuid}.pdf"
        report_storage_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(report_storage_dir, exist_ok=True)
        report_path = os.path.join(report_storage_dir, report_filename)

        generate_pdf_report(final_state.analysis_report, report_path)

        # --- FINAL CLEANUP (Delete temp dir and uploaded files) ---
        shutil.rmtree(temp_dir, ignore_errors=True)
        task.delete()

        return JsonResponse({
            "status": "success",
            "message": "Analysis complete.",
            "report_url": f"{settings.MEDIA_URL}reports/{report_filename}"
        })

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        # We don't delete the task here to allow inspection of the failed file paths
        return JsonResponse({"error": f"Internal workflow error: {e}"}, status=500)