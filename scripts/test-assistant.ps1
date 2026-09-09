$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\python.exe -m unittest discover -s tests/assistant -v
if ($LASTEXITCODE -ne 0) { throw 'Assistant tests failed.' }
