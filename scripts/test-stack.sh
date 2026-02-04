#!/bin/bash
# Wingman Test Stack Management Script
#
# Provides one-command operations for the test container stack.
# Containers are labeled with wingman.test=true for safety policy.
#
# Usage:
#   ./scripts/test-stack.sh up       # Start test stack
#   ./scripts/test-stack.sh down     # Stop test stack
#   ./scripts/test-stack.sh reset    # Reset (down -v, then up)
#   ./scripts/test-stack.sh status   # Show container status
#   ./scripts/test-stack.sh logs     # Show container logs
#   ./scripts/test-stack.sh health   # Run health checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.test-stack.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

cmd_up() {
    log_info "Starting Wingman test stack..."
    check_docker
    
    docker compose -f "$COMPOSE_FILE" up -d
    
    log_info "Waiting for containers to be healthy..."
    sleep 5
    
    # Check health of each container
    local all_healthy=true
    for container in wingman-test-nginx wingman-test-redis wingman-test-postgres wingman-test-alpine; do
        if docker ps --filter "name=$container" --filter "status=running" --format "{{.Names}}" | grep -q "$container"; then
            log_success "$container is running"
        else
            log_warn "$container is not running yet"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        log_success "Test stack is ready!"
        echo ""
        echo "Run integration tests with:"
        echo "  WINGMAN_EXECUTION_MODE=integration pytest tests/ -v -k integration"
    else
        log_warn "Some containers may still be starting. Run 'status' to check."
    fi
}

cmd_down() {
    log_info "Stopping Wingman test stack..."
    check_docker
    
    docker compose -f "$COMPOSE_FILE" down
    
    log_success "Test stack stopped"
}

cmd_reset() {
    log_info "Resetting Wingman test stack (removing volumes)..."
    check_docker
    
    docker compose -f "$COMPOSE_FILE" down -v
    
    log_info "Starting fresh test stack..."
    docker compose -f "$COMPOSE_FILE" up -d
    
    sleep 5
    log_success "Test stack reset complete"
    
    cmd_status
}

cmd_status() {
    log_info "Test stack status:"
    check_docker
    
    echo ""
    echo "Containers:"
    docker ps --filter "label=wingman.test=true" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "Network:"
    docker network ls --filter "label=wingman.test=true" --format "table {{.Name}}\t{{.Driver}}"
    
    echo ""
    echo "Volumes:"
    docker volume ls --filter "label=com.docker.compose.project=wingman-test-stack" --format "table {{.Name}}\t{{.Driver}}"
}

cmd_logs() {
    log_info "Test stack logs (last 50 lines each):"
    check_docker
    
    for container in wingman-test-nginx wingman-test-redis wingman-test-postgres wingman-test-alpine; do
        echo ""
        echo "=== $container ==="
        docker logs --tail 50 "$container" 2>&1 || echo "(no logs or container not running)"
    done
}

cmd_health() {
    log_info "Running health checks..."
    check_docker
    
    echo ""
    
    # Check nginx
    echo -n "nginx (http://localhost:8081): "
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8081 | grep -q "200"; then
        log_success "OK"
    else
        log_error "FAILED"
    fi
    
    # Check redis
    echo -n "redis (localhost:6380): "
    if docker exec wingman-test-redis redis-cli ping | grep -q "PONG"; then
        log_success "OK"
    else
        log_error "FAILED"
    fi
    
    # Check postgres
    echo -n "postgres (localhost:5433): "
    if docker exec wingman-test-postgres pg_isready -U testuser -d testdb | grep -q "accepting"; then
        log_success "OK"
    else
        log_error "FAILED"
    fi
    
    # Check alpine
    echo -n "alpine (container running): "
    if docker ps --filter "name=wingman-test-alpine" --filter "status=running" --format "{{.Names}}" | grep -q "wingman-test-alpine"; then
        log_success "OK"
    else
        log_error "FAILED"
    fi
    
    echo ""
    log_info "Health check complete"
}

cmd_help() {
    echo "Wingman Test Stack Management"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  up       Start the test container stack"
    echo "  down     Stop the test container stack"
    echo "  reset    Reset stack (down -v, then up) - clears all data"
    echo "  status   Show container status"
    echo "  logs     Show container logs"
    echo "  health   Run health checks on all containers"
    echo "  help     Show this help message"
    echo ""
    echo "Environment variables for integration tests:"
    echo "  WINGMAN_EXECUTION_MODE=integration"
    echo "  WINGMAN_CONTAINER_ALLOWLIST=wingman-test-nginx,wingman-test-redis,..."
}

# Main command dispatcher
case "${1:-help}" in
    up)
        cmd_up
        ;;
    down)
        cmd_down
        ;;
    reset)
        cmd_reset
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs
        ;;
    health)
        cmd_health
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        cmd_help
        exit 1
        ;;
esac
