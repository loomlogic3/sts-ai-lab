#!/bin/bash

MODEL="llama3.2:1b"
PROMPT_FILE="scripts/prompts/sts_mentor.md"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Prompt file not found: $PROMPT_FILE"
  exit 1
fi

cat "$PROMPT_FILE"
echo ""
echo "User question:"
read -r USER_QUESTION

FULL_PROMPT="$(cat "$PROMPT_FILE")

User question:
$USER_QUESTION"

ollama run "$MODEL" "$FULL_PROMPT"
