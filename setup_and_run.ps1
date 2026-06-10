$ErrorActionPreference = "Stop"

function Get-PythonCommand {
    $candidates = @(
        @{ Cmd = "py"; Args = @("-3.11") },
        @{ Cmd = "py"; Args = @("-3.10") },
        @{ Cmd = "python"; Args = @() },
        @{ Cmd = "python3"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        try {
            $versionText = & $candidate.Cmd @($candidate.Args + @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")) 2>$null
            if ($LASTEXITCODE -eq 0 -and ($versionText -eq "3.10" -or $versionText -eq "3.11")) {
                return $candidate
            }
        } catch {}
    }

    throw "Python 3.10 or 3.11 is required for Basic Pitch/TensorFlow. Install Python 3.11, then run this again."
}

$python = Get-PythonCommand
& $python.Cmd @($python.Args + @("-m", "venv", ".venv"))
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
npm --prefix frontend install
npm --prefix frontend run build

Write-Host ""
Write-Host "Starting FChord Web App on http://localhost:8000"
Write-Host "Keep this terminal open while using the app. Because naturally servers need to exist to serve things."
Write-Host ""
Start-Process "http://localhost:8000"
& ".\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 120
