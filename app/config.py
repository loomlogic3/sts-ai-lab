"""
STS AI Lab Configuration
"""

DEFAULT_MODEL = "llama3.2:1b"

DEFAULT_TEMPERATURE = 0.2

PROMPT_DIRECTORY = "scripts/prompts"

EXPERIMENT_DIRECTORY = "experiments"

# Resource budgets for lightweight local hardware.
MAX_CONVERSATION_CHARS = 1000
MAX_CALLER_CONTEXT_CHARS = 4000
MAX_MENTOR_KNOWLEDGE_CHARS = 1200
MAX_PROMPT_CHARS = 12000
MAX_KNOWLEDGE_DOCUMENTS = 3
MAX_KNOWLEDGE_CHARS_PER_DOCUMENT = 4000
MAX_FILE_READ_CHARS = 20000
MAX_SEARCH_FILE_CHARS = 20000
MAX_SEARCH_FILES = 200
MAX_SEARCH_RESULTS = 50
MAX_CODE_EXPLANATION_CHARS = 2500
OLLAMA_NUM_CONTEXT = 1024
OLLAMA_DEFAULT_NUM_PREDICT = 120
# CPU-only local inference can exceed one minute for full STS prompts even when
# short warm requests complete quickly. Keep the transport bounded while
# allowing cold model loading and constrained-hardware prompt evaluation.
OLLAMA_TIMEOUT_SECONDS = 180
OLLAMA_KEEP_ALIVE = "30m"
MENTOR_NUM_PREDICT = 80
CLOUD_MODEL_TIMEOUT_SECONDS = 90
