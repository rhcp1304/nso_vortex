import requests
import json
import os

# Define the base URL of your Django server.
# This assumes the server is running locally on port 8000.
BASE_URL = "http://127.0.0.1:8000/meeting-agent/"
ENDPOINT = "process-transcript/"


def test_api():
    """
    Sends a POST request with a sample meeting transcript to the Django backend
    and prints the structured response.
    """
    sample_transcript = """
    Attendees: John, Jane, Sarah
    Date: October 26, 2023

    Jane: Hi everyone, thanks for joining. Let's start with the Q3 marketing campaign. The preliminary results are in, and we've seen a 15% increase in lead generation.
    John: That's great news, Jane. I've been working on the new website landing page to support the campaign. I should have a final draft ready for review by next Friday.
    Sarah: Excellent. Regarding the social media strategy, I think we should increase the ad spend on Instagram. I'll get the budget analysis completed and send it to John and Jane for approval by the end of the week.
    Jane: Sounds good, Sarah. John, once you have the final draft of the landing page, please share it with the team so we can provide feedback before the launch. The goal is to get it live by November 15th.
    John: Will do. Thanks.
    Sarah: I'll also follow up with the creative team about the new ad visuals. I'll ping them for an update tomorrow.
    Jane: Perfect. Let's touch base again next week to review progress.
    """

    # Create the payload with the transcript
    payload = {
        "transcript": sample_transcript
    }

    try:
        # Send the POST request to the API endpoint
        print(f"Sending transcript to {BASE_URL}{ENDPOINT}...")
        response = requests.post(
            f"{BASE_URL}{ENDPOINT}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        # Raise an exception for bad status codes (e.g., 404, 500)
        response.raise_for_status()

        # Print the JSON response from the server
        print("\n--- Response from Server ---")
        print(json.dumps(response.json(), indent=2))

    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred: {e}")
        print("Please make sure your Django server is running.")


if __name__ == "__main__":
    test_api()
