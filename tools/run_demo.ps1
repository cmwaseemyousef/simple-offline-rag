# Runs the sample query for recording a short demo.
param(
    [string]$Query = "What is RAG and why use it?",
    [int]$K = 3,
    [ValidateSet('offline','openai')]
    [string]$Provider = 'offline'
)

Write-Host "Running demo..." -ForegroundColor Cyan
python -m src.app.cli "$Query" --k $K --provider $Provider
