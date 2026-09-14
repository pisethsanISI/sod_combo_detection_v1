# Launches the point-and-click GUI -- browse to your SAP export CSVs and
# click Run Detection. No command line needed after this. Double-click this
# file (or right-click -> Run with PowerShell) any time you have a fresh
# SAP export to check.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Start-Process -FilePath ".\.venv\Scripts\combo-detect-gui.exe"
