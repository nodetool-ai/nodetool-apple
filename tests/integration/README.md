# Integration Tests for nodetool-apple

This directory contains integration tests for Apple-specific nodes that run on actual macOS systems.

## Overview

These tests verify that Apple nodes work correctly on macOS by:
- Testing actual macOS APIs (PyObjC, CoreServices, etc.)
- Running native macOS commands (shortcuts, mdfind, etc.)
- Interacting with macOS system services (Clipboard, Dictionary, etc.)

## Tests Included

### test_shortcuts_integration.py
- Tests the Shortcuts CLI availability
- Tests listing shortcuts
- Verifies shortcuts node behavior on macOS

### test_dictionary_integration.py
- Tests macOS Dictionary.app integration
- Tests word lookups using CoreServices APIs
- Verifies caching behavior for dictionary searches

### test_screen_integration.py
- Tests screen capture functionality
- Tests both full screen and region capture
- Verifies image output from capture operations

### test_speech_integration.py
- Tests text-to-speech functionality
- Tests different voice options
- Verifies speech synthesis works without errors

### test_clipboard_integration.py
- Tests reading from and writing to the macOS clipboard
- Tests text clipboard operations
- Verifies clipboard state management

### test_spotlight_integration.py
- Tests Spotlight search using mdfind
- Tests query limits and filtering
- Verifies mdfind CLI availability

## Running Tests Locally

To run these tests locally on macOS:

```bash
# Install dependencies
pip install -e .
pip install -r requirements-dev.txt

# Run integration tests
pytest tests/integration/ -v
```

## Running on GitHub Actions

These tests run automatically on macOS runners via the `integration-tests-macos.yml` workflow:
- Triggered on push to main/develop branches
- Triggered on pull requests
- Can be manually triggered via workflow_dispatch

## Requirements

- macOS 12+ (for shortcuts CLI)
- Python 3.11+
- PyObjC dependencies (installed automatically on macOS)
- Access to macOS system services

## Notes

- Some nodes (Notes, Calendar, Messages) require user interaction and are not included in integration tests
- Tests are designed to be non-destructive and not require manual setup
- Screen capture tests may produce empty images in headless environments
- Speech tests don't verify audio output, only that synthesis starts successfully
