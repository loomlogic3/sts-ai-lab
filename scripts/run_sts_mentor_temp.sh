#!/bin/bash

# Legacy experimental entry point. Governed production Python execution uses:
# python3 -m app.cli mentor
MODEL="llama3.2:1b"
PROMPT_FILE="scripts/prompts/sts_mentor.md"
TEMPERATURE="${1:-0.2}"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Prompt file not found: $PROMPT_FILE"
  exit 1
fi

echo "Using model: $MODEL"
echo "Using temperature: $TEMPERATURE"
echo ""

echo "User question:"
read -r USER_QUESTION

FULL_PROMPT="$(cat "$PROMPT_FILE")

User question:
$USER_QUESTION"

ollama run "$MODEL" "$FULL_PROMPT" --temperature "$TEMPERATURE"
