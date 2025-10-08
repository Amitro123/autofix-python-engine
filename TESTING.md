# Testing Guide

This document provides instructions for testing the AutoFix Python Engine.

## Unit Tests

To run the unit tests, use the following command:

```bash
pytest
```

The test suite includes 30 unit tests that cover the core functionality of the tool. The current test coverage is approximately 30%.

## Integration Tests

Integration tests have been performed to validate all major features of the tool, including:

-   All supported error types
-   Large file handling (200+ lines)
-   Cross-platform compatibility (Windows and Linux)

## Manual Testing

To manually test the tool, you can use the following command:

```bash
python -m autofix.cli.autofix_cli_interactive your_script.py
```

Replace `your_script.py` with the path to a Python script that contains one or more errors.

## Performance Testing

Performance tests have been conducted to ensure that the tool can process files of various sizes in a timely manner. The following are the expected processing times:

-   **Small files** (< 100 lines): < 1 second
-   **Medium files** (100-500 lines): 1-3 seconds
-   **Large files** (500+ lines): 3-5 seconds