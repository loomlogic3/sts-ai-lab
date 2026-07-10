from app.input_classifier import InputType, classify


def test_question_is_ai_request():
    assert classify("what is STS AI Lab?") == InputType.AI_REQUEST


def test_slash_command_is_command():
    assert classify("/memory") == InputType.AI_REQUEST


def test_statement_is_statement():
    assert classify("My project name is MemoryCheck.") == InputType.STATEMENT
