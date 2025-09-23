from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .ai_service import main_workflow
import logging

# Set up logging for the Django view.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@csrf_exempt
def process_transcript(request):
    """
    This view processes a meeting transcript using the AI agent workflow.
    It expects a JSON payload with a 'transcript' field.
    """
    logger.info("Received request to process transcript.")

    if request.method == 'POST':
        try:
            # Decode the JSON payload from the request body.
            data = json.loads(request.body)
            transcript = data.get('transcript')

            if not transcript:
                logger.error("No transcript provided in the request body.")
                return JsonResponse({'status': 'error', 'message': 'No transcript provided.'}, status=400)

            # Call the agentic workflow to process the transcript.
            logger.info("Passing transcript to agent for processing.")
            result = main_workflow(transcript)

            # The agent returns a dictionary, which Django converts to JSON.
            return JsonResponse(result, status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body.")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, status=500)
    else:
        # Handle non-POST requests.
        logger.warning(f"Unsupported request method: {request.method}")
        return JsonResponse({'status': 'error', 'message': 'Only POST requests are supported.'}, status=405)
