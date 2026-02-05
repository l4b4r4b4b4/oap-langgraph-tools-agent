import logging
import os

# from langfuse.callback import CallbackHandler
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
from system_2.cache.redis_cache import RedisCompatibleCache
from system_2.cache.cache import ToolsetCache

import json
import platform
from system_1.agent import graph
from system_0.config import settings

# Import routers
from system_0.routers import health, system_0

# from system_0.routers.system_1 import setup_agent_routes
from system_0.routers.system_2 import router as system_2_cache_router
from copilotkit.integrations.fastapi import add_fastapi_endpoint

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent

# Check environment - use NODE_ENV to be consistent with Node.js conventions
load_dotenv()
environment = os.getenv("NODE_ENV", "development")
log_level = logging.INFO
# log_level = logging.DEBUG if environment.lower() == "development" else logging.INFO

# Only enable reload in development mode
enable_reload = environment.lower() == "development"
logging.basicConfig(level=log_level)

logger = logging.getLogger(__name__)

ToolsetCache.register_cache_implementation(RedisCompatibleCache)


# Set Redis-compatible server URL from environment (default to KeyDB)

redis_url = settings.er_cache_url


# Initialize base caches that will be commonly used
def initialize_caches():
    """Initialize common caches during startup"""
    try:
        # Create standard toolset caches
        time_cache = ToolsetCache.get_cache_for_tool("time_toolset")
        logger.debug(f"time_cache: {repr(time_cache)}")
        math_cache = ToolsetCache.get_cache_for_tool("math_toolset")
        logger.debug(f"math_cache: {repr(math_cache)}")

        cache_tools_cache = ToolsetCache.get_cache_for_tool("cache_toolset")
        logger.debug(f"cache_tools_cache: {repr(cache_tools_cache)}")

        # Mark caches as initialized in environment for other processes
        os.environ["MCP_CACHES_INITIALIZED"] = "1"

        logger.info(f"Initialized caches: {list(ToolsetCache._cache_registry.keys())}")
        return True
    except Exception as e:
        logger.error(f"Error initializing caches: {e}")
        return False


# DB_URI = f"postgresql://{os.environ.get('LANGGRAPH_DB_WRITE_USER')}:{os.environ.get('LANGGRAPH_DB_WRITE_PASS')}@app-db:5432/{os.environ.get('LANGGRAPH_DB_NAME')}"

# Create the FastAPI app
app = FastAPI(
    title="Fractal Agents API",
    description="API for interacting with Fractal AI Agents",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Include routers
app.include_router(health.router)
app.include_router(system_0.router)
# setup_agent_routes(app)
app.include_router(system_2_cache_router)

sdk = CopilotKitRemoteEndpoint(
    agents=lambda context: [
        LangGraphAgent(
            name="fractal_agent",
            description="Default Fractal AI agent.",
            graph=graph,
        )
    ]
)
add_fastapi_endpoint(app, sdk, "/api/v1/system_1", use_thread_pool=True)

# Set up CopilotKit routes


def get_compute_capabilities():
    """Get basic system information"""
    compute_info = {
        "cpu": {"info": platform.processor() or "Unknown CPU"},
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        },
    }
    return compute_info


@app.on_event("startup")
async def startup_event():
    """Initialize components during startup"""
    try:
        # Check system capabilities
        compute_info = get_compute_capabilities()
        logger.info(f"System info: {json.dumps(compute_info['system'], indent=2)}")
        logger.info(f"Using CPU: {compute_info['cpu']['info']}")

        # Get Redis client
        redis_client = RedisCompatibleCache.get_redis_client()

        # Find existing caches in Redis
        existing_cache_keys_raw = redis_client.keys("cache_registry:*")
        existing_caches = []

        # Handle the result properly regardless of type
        if existing_cache_keys_raw:
            if isinstance(existing_cache_keys_raw, list):
                # Process list of keys
                for key in existing_cache_keys_raw:
                    if isinstance(key, bytes):
                        cache_name = key.decode().replace("cache_registry:", "")
                    else:
                        cache_name = str(key).replace("cache_registry:", "")
                    existing_caches.append(cache_name)
            else:
                # Handle single key case
                if isinstance(existing_cache_keys_raw, bytes):
                    cache_name = existing_cache_keys_raw.decode().replace(
                        "cache_registry:", ""
                    )
                else:
                    cache_name = str(existing_cache_keys_raw).replace(
                        "cache_registry:", ""
                    )
                existing_caches.append(cache_name)

        logger.info(
            f"Found {len(existing_caches)} existing caches in Redis: {existing_caches}"
        )

        # Initialize each cache
        for cache_name in existing_caches:
            RedisCompatibleCache.get_cache_for_tool(cache_name)

        # Initialize standard caches if not already in Redis
        _ = ToolsetCache.get_cache_for_tool("time_toolset")
        _ = ToolsetCache.get_cache_for_tool("math_toolset")
        _ = ToolsetCache.get_cache_for_tool("cache_toolset")

        logger.info(f"Initialized caches: {list(ToolsetCache._cache_registry.keys())}")

    except Exception as e:
        logger.error(f"Error during cache initialization: {e}")


# Clean up at shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Flush caches when the app shuts down"""
    logger.info("Flushing caches before shutdown...")
    try:
        # Get all initialized caches and flush them
        for cache_name, cache in ToolsetCache._cache_registry.items():
            if hasattr(cache, "flush") and callable(cache.flush):
                try:
                    cache.flush()
                    logger.info(f"Flushed cache: {cache_name}")
                except Exception as e:
                    logger.error(f"Error flushing cache {cache_name}: {e}")
    except Exception as e:
        logger.error(f"Error during cache shutdown: {e}")


def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "7373"))
    hostname = str(os.getenv("HOSTNAME", "0.0.0.0"))

    if enable_reload:
        logger.info("Starting server in DEVELOPMENT mode with hot reload enabled")
        uvicorn.run(
            "src.app:app",
            host=hostname,
            port=port,
            reload=True,
            reload_dirs=(["."]),
        )
    else:
        # Determine worker count based on environment
        if environment == "staging":
            worker_count = int(os.getenv("WORKER_COUNT", "1"))  # Default 1 for staging
        elif environment == "production":
            worker_count = int(
                os.getenv("WORKER_COUNT", "5")
            )  # Default 5 for production
        else:
            worker_count = int(
                os.getenv("WORKER_COUNT", "2")
            )  # Default 2 for other environments

        logger.info(
            f"Starting server in {environment.upper()} mode with {worker_count} workers"
        )

        # Using Uvicorn with workers
        uvicorn.run(
            "src.app:app",
            host=hostname,
            port=port,
            # workers=worker_count,
        )


if __name__ == "__main__":
    main()
