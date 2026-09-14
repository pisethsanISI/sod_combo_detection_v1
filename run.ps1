# Runs the combination-rule detector against the bundled sample data.
# Edit the paths below to point at real converted SAP data instead --
# e.g. ..\SOD_Detection\data\from_manual_export\*.csv -- once you have it.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

New-Item -ItemType Directory -Force -Path "output" | Out-Null

& ".\.venv\Scripts\combo-detect.exe" `
    --ruleset "ruleset\sap_sod_combination_ruleset.json" `
    --role-tcodes "data\sample_role_tcodes.csv" `
    --user-roles "data\sample_user_roles.csv" `
    --composite-roles "data\sample_composite_roles.csv" `
    --output "output\sod_combination_report.pdf" `
    --excel-output "output\sod_combination_report.xlsx"

Write-Host "`nOpen output\sod_combination_report.pdf or .xlsx to view the report."
