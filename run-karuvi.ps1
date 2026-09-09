param(
    [Parameter(Position = 0)]
    [string]$RepoPath = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

# Check Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker Desktop is not installed."
    Write-Host "Install it from https://www.docker.com/products/docker-desktop/"
    exit 1
}

# Check Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "Docker Desktop is not running. Please start it and try again."
    exit 1
}

# Resolve and validate repository path
try {
    $RepoPath = (Resolve-Path -LiteralPath $RepoPath -ErrorAction Stop).Path
} catch {
    Write-Host "Repository path not found: $RepoPath"
    exit 1
}

if (-not (Test-Path -LiteralPath $RepoPath -PathType Container)) {
    Write-Host "Path is not a directory: $RepoPath"
    exit 1
}

Write-Host "Starting Karuvi..."
Write-Host "Analysing: $RepoPath"
Write-Host "Open http://localhost:8000 when ready."
Write-Host ""

docker run --rm `
    -p 8000:8000 `
    -v "${RepoPath}:/workspace:ro" `
    ghcr.io/not-that-deep-26/karuvi:latest `
    /workspace --serve
