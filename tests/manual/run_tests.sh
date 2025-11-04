#!/bin/bash
# Run manual tests with project .env taking precedence over global exports

# Unset global OPENAI_API_KEY so config loads from project .env
unset OPENAI_API_KEY

# Run the test script
exec python3 "$@"
