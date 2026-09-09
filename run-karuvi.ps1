$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker Desktop is not installed."
    Write-Host "Install it from https://www.docker.com/products/docker-desktop/"
    exit 1
}

try {
    docker info | Out-Null
} catch {
    Write-Host "Docker Desktop is not running. Please start it and try again."
    exit 1
}

$RepoPath = (Get-Location).Path

Write-Host "Starting Karuvi..."
Write-Host "Analysing: $RepoPath"
Write-Host ""

docker run --rm `
    -p 8000:8000 `
    -v "${RepoPath}:/workspace:ro" `
    ghcr.io/not-that-deep-26/karuvi:latest `
    /workspace --serve
