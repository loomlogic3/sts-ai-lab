"""
Response Processor for the STS AI Engine.
"""


def clean_response(response: str) -> str:
    """
    Clean and normalize model output before displaying it.
    """

    cleaned = response.strip()

    # Remove common over-friendly openings from small local models.
    unwanted_openings = [
        "Hello! As your STS Mentor,",
        "I'm STS Mentor,",
        "As STS Mentor,",
    ]

    for opening in unwanted_openings:
        if cleaned.startswith(opening):
            cleaned = cleaned.replace(opening, "", 1).strip()

    return cleaned
