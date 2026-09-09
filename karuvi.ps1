<#
.SYNOPSIS
Karuvi Windows Launcher

.DESCRIPTION
A wrapper script that runs the Karuvi Whole-Repository Analyzer via Docker on Windows.
It seamlessly translates local paths and passes all CLI arguments to the containerized application.

.EXAMPLE
karuvi C:\Projects\my-project --serve
#>

$ErrorActionPreference = "Stop"

# Check Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Karuvi requires Docker Desktop on Windows for native compatibility." -ForegroundColor Red
    Write-Host "Please install it from https://www.docker.com/products/docker-desktop/"
    exit 1
}

# Check Docker is running
try {
    $null = docker info 2>&1
} catch {
    Write-Host "Docker Desktop is not running. Please start it and try again." -ForegroundColor Red
    exit 1
}

# Default settings
$ImageName = "ghcr.io/not-that-deep-26/karuvi:latest"

# Parse arguments to find the repository path
$DockerArgs = @()
$RepoPath = $null
$SkipNext = $false

for ($i = 0; $i -lt $args.Count; $i++) {
    if ($SkipNext) {
        $SkipNext = $false
        continue
    }

    $arg = $args[$i]

    if ($arg -eq "--repo" -or $arg -eq "-r") {
        if ($i + 1 -lt $args.Count) {
            $RepoPath = $args[$i+1]
            $DockerArgs += "--repo"
            $DockerArgs += "/workspace"
            $SkipNext = $true
        } else {
            $DockerArgs += $arg
        }
    }
    elseif ($null -eq $RepoPath -and -not $arg.StartsWith("-")) {
        # Avoid treating subcommands as paths
        if ($arg -in @("onboard", "explore", "analyze", "export", "explain")) {
            $DockerArgs += $arg
        } else {
            try {
                $resolved = Resolve-Path -LiteralPath $arg -ErrorAction SilentlyContinue
                if ($resolved -and (Test-Path -LiteralPath $resolved.Path -PathType Container)) {
                    $RepoPath = $resolved.Path
                    $DockerArgs += "/workspace"
                } else {
                    $DockerArgs += $arg
                }
            } catch {
                $DockerArgs += $arg
            }
        }
    }
    else {
        $DockerArgs += $arg
    }
}

# If no path was identified, default to current directory to allow interactive prompts to work locally
if ($null -eq $RepoPath) {
    $RepoPath = (Get-Location).Path
} else {
    $RepoPath = (Resolve-Path -LiteralPath $RepoPath -ErrorAction Stop).Path
}

# Execute Docker
$DockerCmd = @("docker", "run", "-it", "--rm", "-p", "8000:8000", "-v", "$($RepoPath):/workspace:ro", $ImageName)
$DockerCmd += $DockerArgs

try {
    & $DockerCmd[0] $DockerCmd[1..($DockerCmd.Count-1)]
} catch {
    exit $LASTEXITCODE
}
exit $LASTEXITCODE
