"""Main Robyn application entry point.

This module provides the Robyn web server for the OAP LangGraph Tools Agent.
It implements a LangGraph-compatible API for Open Agent Platform compatibility.
"""

from robyn import Robyn
from robyn.openapi import OpenAPI, OpenAPIInfo

from robyn_server.auth import auth_middleware
from robyn_server.config import get_config
from robyn_server.models import HealthResponse, ServiceInfoResponse
from robyn_server.openapi_spec import (
    API_DESCRIPTION,
    API_TITLE,
    API_VERSION,
    get_openapi_spec,
)
from robyn_server.routes import (
    register_assistant_routes,
    register_run_routes,
    register_stream_routes,
    register_thread_routes,
)
from robyn_server.routes.mcp import register_mcp_routes
from robyn_server.routes.metrics import register_metrics_routes
from robyn_server.routes.store import register_store_routes

# Create custom OpenAPI configuration
openapi_info = OpenAPIInfo(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
)
openapi = OpenAPI(info=openapi_info)

# Override with our complete custom spec
openapi.openapi_spec = get_openapi_spec()
openapi.openapi_file_override = True

# Create the Robyn application with custom OpenAPI
app = Robyn(__file__, openapi=openapi)


# Register authentication middleware using decorator pattern
@app.before_request()
async def middleware_wrapper(request):
    """Wrap auth middleware for Robyn's decorator pattern."""
    return await auth_middleware(request)


# Register API routes
register_assistant_routes(app)
register_thread_routes(app)
register_run_routes(app)
register_stream_routes(app)
register_metrics_routes(app)
register_store_routes(app)
register_mcp_routes(app)


# ============================================================================
# Health & Info Endpoints
# ============================================================================


@app.get("/health")
async def health() -> dict:
    """Health check endpoint (public - no auth required).

    Returns:
        JSON response with status "ok" if the server is healthy.
    """
    response = HealthResponse()
    return response.model_dump()


@app.get("/ok")
async def ok() -> dict:
    """LangGraph-style health check endpoint (public - no auth required).

    Returns:
        JSON response with {"ok": true} matching LangGraph API shape.
    """
    return {"ok": True}


@app.get("/")
async def root() -> dict:
    """Root endpoint with service information (public - no auth required).

    Returns:
        JSON response with service name, runtime, and version.
    """
    response = ServiceInfoResponse()
    return response.model_dump()


@app.get("/info")
async def info() -> dict:
    """Detailed service information endpoint (public - no auth required).

    Returns LangGraph-compatible service information including:
    - Version and build info
    - Capability flags
    - Available graphs
    - Runtime details

    Returns:
        JSON response with service details and configuration status.
    """
    import os
    import subprocess
    from datetime import datetime

    config = get_config()

    # Try to get git commit hash
    commit_hash = "unknown"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            commit_hash = result.stdout.strip()
    except Exception:
        pass

    # Get build date from environment or use current date
    build_date = os.getenv("BUILD_DATE", datetime.now().strftime("%Y-%m-%d"))

    return {
        # Core identification
        "service": "oap-langgraph-tools-agent",
        "runtime": "robyn",
        "version": "0.1.0",
        # Build information
        "build": {
            "commit": commit_hash,
            "date": build_date,
            "python": os.sys.version.split()[0],
        },
        # Capability flags (what features are available)
        "capabilities": {
            "streaming": True,  # SSE streaming supported
            "store": True,  # Store API supported
            "crons": False,  # Cron jobs not yet implemented
            "a2a": False,  # Agent-to-Agent not yet implemented
            "mcp": True,  # MCP endpoints implemented
            "metrics": True,  # Prometheus metrics available
        },
        # Available agent graphs
        "graphs": ["agent"],
        # Configuration status
        "config": {
            "supabase_configured": config.supabase.is_configured,
            "llm_configured": bool(
                config.llm.openai_api_key or config.llm.openai_api_base
            ),
        },
        # Tier completion status
        "tiers": {
            "tier1": True,  # Core CRUD + Streaming
            "tier2": True,  # Search/Count/List
            "tier3": "partial",  # Metrics + Store (Crons/A2A/MCP pending)
        },
    }


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Start the Robyn server."""
    config = get_config()
    print(f"Starting Robyn server on {config.server.host}:{config.server.port}")
    app.start(
        host=config.server.host,
        port=config.server.port,
    )


if __name__ == "__main__":
    main()
