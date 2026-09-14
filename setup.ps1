# One-time setup: creates .venv and installs this package into it.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -e ".[dev]"

Write-Host "Setup complete. Run '.\run.ps1' to generate a sample report."
