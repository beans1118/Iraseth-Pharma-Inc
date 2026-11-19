# Run from a normal PowerShell terminal; no administrator rights needed.
[CmdletBinding()]
param(
    [ValidatePattern('^(iraseth|iraseth_dev|iraseth_local_[a-z][a-z0-9_]{0,39})$')]
    [string]$Database = 'iraseth',
    [string]$MongoUri = 'mongodb://127.0.0.1:27017/?replicaSet=rs0',
    [switch]$Apply,
    [switch]$Status,
    [switch]$SkipDependencies
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'
if ($Apply -and $Status) { throw 'Choose -Apply or read-only -Status.' }
if ($Database -match 'prod|staging') { throw 'Production/staging names are refused.' }

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Executable (exit $LASTEXITCODE). Setup stopped." }
}

Push-Location $repoRoot
try {
    if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw 'Install Node.js 24 (includes npm), then open a new terminal.'
    }
    $nodeVersion = & node --version
    if ($LASTEXITCODE -ne 0 -or $nodeVersion -notmatch '^v24\.') { throw 'Use Node.js 24 for this repository.' }
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        if ($Status -or $SkipDependencies) { throw 'Missing backend/.venv. Run setup without -Status/-SkipDependencies first.' }
        if (Get-Command py -ErrorAction SilentlyContinue) {
            Invoke-Checked 'py' @('-3.12', '-m', 'venv', 'backend/.venv')
        } else {
            $pythonVersion = & python --version
            if ($LASTEXITCODE -ne 0 -or $pythonVersion -notmatch '^Python 3\.12\.') { throw 'Install Python 3.12 with the Python launcher.' }
            Invoke-Checked 'python' @('-m', 'venv', 'backend/.venv')
        }
    }
    $pythonVersion = & $pythonExe --version
    if ($LASTEXITCODE -ne 0 -or $pythonVersion -notmatch '^Python 3\.12\.') { throw 'This repository uses Python 3.12; existing virtual environment preserved.' }
    if (-not $Status -and -not $SkipDependencies) {
        Invoke-Checked $pythonExe @('-m', 'pip', 'install', '-r', 'backend/requirements-dev.txt')
        foreach ($appDirectory in @('frontend', 'storefront-next')) {
            Push-Location (Join-Path $repoRoot $appDirectory)
            try { Invoke-Checked 'npm.cmd' @('ci') } finally { Pop-Location }
        }
    }
    $environmentArgs = @('backend/tools/configure_local.py', '--database', $Database, '--uri', $MongoUri)
    if ($Status) { $environmentArgs += '--check' }
    Invoke-Checked $pythonExe $environmentArgs
    $catalogArgs = @('backend/tools/setup_local_catalog.py', '--database', $Database, '--uri', $MongoUri)
    if ($Apply) { $catalogArgs += @('--apply', '--confirm-database', $Database) }
    Invoke-Checked $pythonExe $catalogArgs
    Write-Host 'See DEVELOPER-SETUP.md for account setup, startup, testing and troubleshooting.'
} finally {
    Pop-Location
}
