# Wingman Test Stack Management Script (PowerShell)
#
# Provides one-command operations for the test container stack.
# Containers are labeled with wingman.test=true for safety policy.
#
# Usage:
#   .\scripts\test-stack.ps1 up       # Start test stack
#   .\scripts\test-stack.ps1 down     # Stop test stack
#   .\scripts\test-stack.ps1 reset    # Reset (down -v, then up)
#   .\scripts\test-stack.ps1 status   # Show container status
#   .\scripts\test-stack.ps1 logs     # Show container logs
#   .\scripts\test-stack.ps1 health   # Run health checks

param(
    [Parameter(Position=0)]
    [ValidateSet('up', 'down', 'reset', 'status', 'logs', 'health', 'help')]
    [string]$Command = 'help'
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $ProjectRoot "docker-compose.test-stack.yml"

function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Success { param($Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warn { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Err { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

function Test-Docker {
    try {
        $null = docker info 2>&1
        return $true
    } catch {
        Write-Err "Docker is not running or not installed"
        exit 1
    }
}

function Invoke-Up {
    Write-Info "Starting Wingman test stack..."
    Test-Docker
    
    docker compose -f $ComposeFile up -d
    
    Write-Info "Waiting for containers to be healthy..."
    Start-Sleep -Seconds 5
    
    $containers = @("wingman-test-nginx", "wingman-test-redis", "wingman-test-postgres", "wingman-test-alpine")
    $allHealthy = $true
    
    foreach ($container in $containers) {
        $running = docker ps --filter "name=$container" --filter "status=running" --format "{{.Names}}"
        if ($running -match $container) {
            Write-Success "$container is running"
        } else {
            Write-Warn "$container is not running yet"
            $allHealthy = $false
        }
    }
    
    if ($allHealthy) {
        Write-Success "Test stack is ready!"
        Write-Host ""
        Write-Host "Run integration tests with:"
        Write-Host '  $env:WINGMAN_EXECUTION_MODE="integration"; pytest tests/ -v -k integration'
    } else {
        Write-Warn "Some containers may still be starting. Run 'status' to check."
    }
}

function Invoke-Down {
    Write-Info "Stopping Wingman test stack..."
    Test-Docker
    
    docker compose -f $ComposeFile down
    
    Write-Success "Test stack stopped"
}

function Invoke-Reset {
    Write-Info "Resetting Wingman test stack (removing volumes)..."
    Test-Docker
    
    docker compose -f $ComposeFile down -v
    
    Write-Info "Starting fresh test stack..."
    docker compose -f $ComposeFile up -d
    
    Start-Sleep -Seconds 5
    Write-Success "Test stack reset complete"
    
    Invoke-Status
}

function Invoke-Status {
    Write-Info "Test stack status:"
    Test-Docker
    
    Write-Host ""
    Write-Host "Containers:"
    docker ps --filter "label=wingman.test=true" --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
    
    Write-Host ""
    Write-Host "Network:"
    docker network ls --filter "label=wingman.test=true" --format "table {{.Name}}`t{{.Driver}}"
}

function Invoke-Logs {
    Write-Info "Test stack logs (last 50 lines each):"
    Test-Docker
    
    $containers = @("wingman-test-nginx", "wingman-test-redis", "wingman-test-postgres", "wingman-test-alpine")
    
    foreach ($container in $containers) {
        Write-Host ""
        Write-Host "=== $container ===" -ForegroundColor Cyan
        try {
            docker logs --tail 50 $container 2>&1
        } catch {
            Write-Host "(no logs or container not running)"
        }
    }
}

function Invoke-Health {
    Write-Info "Running health checks..."
    Test-Docker
    
    Write-Host ""
    
    # Check nginx
    Write-Host -NoNewline "nginx (http://localhost:8081): "
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8081" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "OK"
        } else {
            Write-Err "FAILED"
        }
    } catch {
        Write-Err "FAILED"
    }
    
    # Check redis
    Write-Host -NoNewline "redis (localhost:6380): "
    $result = docker exec wingman-test-redis redis-cli ping 2>&1
    if ($result -match "PONG") {
        Write-Success "OK"
    } else {
        Write-Err "FAILED"
    }
    
    # Check postgres
    Write-Host -NoNewline "postgres (localhost:5433): "
    $result = docker exec wingman-test-postgres pg_isready -U testuser -d testdb 2>&1
    if ($result -match "accepting") {
        Write-Success "OK"
    } else {
        Write-Err "FAILED"
    }
    
    # Check alpine
    Write-Host -NoNewline "alpine (container running): "
    $running = docker ps --filter "name=wingman-test-alpine" --filter "status=running" --format "{{.Names}}"
    if ($running -match "wingman-test-alpine") {
        Write-Success "OK"
    } else {
        Write-Err "FAILED"
    }
    
    Write-Host ""
    Write-Info "Health check complete"
}

function Show-Help {
    Write-Host "Wingman Test Stack Management"
    Write-Host ""
    Write-Host "Usage: .\test-stack.ps1 <command>"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  up       Start the test container stack"
    Write-Host "  down     Stop the test container stack"
    Write-Host "  reset    Reset stack (down -v, then up) - clears all data"
    Write-Host "  status   Show container status"
    Write-Host "  logs     Show container logs"
    Write-Host "  health   Run health checks on all containers"
    Write-Host "  help     Show this help message"
    Write-Host ""
    Write-Host "Environment variables for integration tests:"
    Write-Host '  $env:WINGMAN_EXECUTION_MODE = "integration"'
    Write-Host '  $env:WINGMAN_CONTAINER_ALLOWLIST = "wingman-test-nginx,wingman-test-redis,..."'
}

# Main command dispatcher
switch ($Command) {
    'up'     { Invoke-Up }
    'down'   { Invoke-Down }
    'reset'  { Invoke-Reset }
    'status' { Invoke-Status }
    'logs'   { Invoke-Logs }
    'health' { Invoke-Health }
    'help'   { Show-Help }
    default  { Show-Help }
}
