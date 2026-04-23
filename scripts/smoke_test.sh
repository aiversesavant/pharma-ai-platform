#!/bin/bash
set -e

echo "Running smoke checks..."

test -f app.py
test -f router.py
test -f compli_pipeline.py
test -d modules
test -d services
test -d data/uploads
test -d data/audit
test -d data/review
test -d data/runtime/vector_store
test -f requirements.txt
test -f .env.example

echo "Smoke checks passed."
