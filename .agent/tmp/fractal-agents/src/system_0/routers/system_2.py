from fastapi import APIRouter, HTTPException
import logging
import os
from typing import List
from pydantic import BaseModel

from system_2.cache.redis_cache import RedisCompatibleCache, safe_redis_result
from system_2.cache.cache import ToolsetCache
from system_0.config import settings


# Define pagination models for request parameters
class PaginationQuery(BaseModel):
    page: int = 1
    page_size: int = 10


# Pagination response model
class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int


router = APIRouter(prefix="/api/v1/system_2", tags=["System 2 | Toolsets & Cache"])
logger = logging.getLogger(__name__)


def discover_toolsets():
    """Force discover available toolsets and their tools"""
    logger.info("Discovering toolsets...")
    try:
        # Get Redis client to find all registered caches
        redis_client = RedisCompatibleCache.get_redis_client()
        cache_registry_keys = safe_redis_result(redis_client.keys("cache_registry:*"))

        # Convert to list of cache names and ensure caches are initialized
        all_cache_names = []
        if cache_registry_keys:
            if isinstance(cache_registry_keys, list):
                for key in cache_registry_keys:
                    cache_name = (
                        key.decode().replace("cache_registry:", "")
                        if isinstance(key, bytes)
                        else str(key).replace("cache_registry:", "")
                    )
                    all_cache_names.append(cache_name)
                    # Ensure cache is initialized locally
                    RedisCompatibleCache.get_cache_for_tool(cache_name)
            else:
                # Handle single key case
                cache_name = (
                    cache_registry_keys.decode().replace("cache_registry:", "")
                    if isinstance(cache_registry_keys, bytes)
                    else str(cache_registry_keys).replace("cache_registry:", "")
                )
                all_cache_names.append(cache_name)
                # Ensure cache is initialized locally
                RedisCompatibleCache.get_cache_for_tool(cache_name)

        # Initialize standard caches if not already discovered
        standard_caches = ["time_toolset", "math_toolset", "cache_toolset"]
        for cache_name in standard_caches:
            if cache_name not in all_cache_names:
                RedisCompatibleCache.get_cache_for_tool(cache_name)
                all_cache_names.append(cache_name)

        logger.info(f"Available caches: {all_cache_names}")
        return True
    except Exception as e:
        logger.error(f"Error discovering toolsets: {e}")
        return False


@router.get("/toolsets")
async def list_toolsets(page: int = 1, page_size: int = 10):
    """List all available toolsets with pagination"""
    try:
        # First ensure all toolsets are discovered
        discovery_successful = discover_toolsets()

        # Get Redis client to find all registered caches (toolsets)
        redis_client = RedisCompatibleCache.get_redis_client()
        cache_registry_keys = safe_redis_result(redis_client.keys("cache_registry:*"))

        # Convert to list of cache/toolset names
        all_toolset_names = []
        if cache_registry_keys:
            if isinstance(cache_registry_keys, list):
                for key in cache_registry_keys:
                    toolset_name = (
                        key.decode().replace("cache_registry:", "")
                        if isinstance(key, bytes)
                        else str(key).replace("cache_registry:", "")
                    )
                    all_toolset_names.append(toolset_name)
            else:
                # Handle single key case
                toolset_name = (
                    cache_registry_keys.decode().replace("cache_registry:", "")
                    if isinstance(cache_registry_keys, bytes)
                    else str(cache_registry_keys).replace("cache_registry:", "")
                )
                all_toolset_names.append(toolset_name)

        # Apply pagination
        total_toolsets = len(all_toolset_names)
        total_pages = max(1, (total_toolsets + page_size - 1) // page_size)
        page = min(max(1, page), total_pages)  # Ensure page is within bounds

        # Get paginated subset of toolset names
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_toolsets)
        paginated_toolset_names = all_toolset_names[start_idx:end_idx]

        # Get summary details for each toolset in the current page
        toolsets_info = []
        for toolset_name in paginated_toolset_names:
            # Count how many tools are in this toolset
            tool_keys = safe_redis_result(redis_client.keys(f"tool:{toolset_name}:*"))
            tool_count = (
                len(tool_keys) if isinstance(tool_keys, list) else 1 if tool_keys else 0
            )

            # Get toolset metadata from Redis
            is_deterministic_raw = safe_redis_result(
                redis_client.get(f"cache_meta:{toolset_name}:deterministic")
            )
            is_deterministic = False
            if is_deterministic_raw:
                is_deterministic = (
                    bool(int(is_deterministic_raw.decode()))
                    if isinstance(is_deterministic_raw, bytes)
                    else bool(int(is_deterministic_raw))
                )

            expiry_raw = safe_redis_result(
                redis_client.get(f"cache_meta:{toolset_name}:expiry")
            )
            expiry = 3600
            if expiry_raw:
                expiry = (
                    int(expiry_raw.decode())
                    if isinstance(expiry_raw, bytes)
                    else int(expiry_raw)
                )

            toolsets_info.append(
                {
                    "name": toolset_name,
                    "deterministic": is_deterministic,
                    "expiry_seconds": None if is_deterministic else expiry,
                    "tools_count": tool_count,
                }
            )

        return {
            "discovery_successful": discovery_successful,
            "items": toolsets_info,
            "total": total_toolsets,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Error listing toolsets: {e}")
        return {
            "error": str(e),
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
        }


@router.get("/toolsets/{toolset_name}/tools")
async def list_toolset_tools(toolset_name: str, page: int = 1, page_size: int = 10):
    """List tools for a specific toolset with pagination"""
    try:
        # Check if toolset exists in Redis
        redis_client = RedisCompatibleCache.get_redis_client()
        toolset_exists = bool(
            safe_redis_result(redis_client.exists(f"cache_registry:{toolset_name}"))
        )

        if not toolset_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Toolset '{toolset_name}' not found in Redis registry",
            )

        # Get all tools registered with this toolset
        tool_keys = safe_redis_result(redis_client.keys(f"tool:{toolset_name}:*"))

        # Process tool keys
        all_tools = []
        if tool_keys:
            if isinstance(tool_keys, list):
                for key in tool_keys:
                    tool_name = (
                        key.decode().replace(f"tool:{toolset_name}:", "")
                        if isinstance(key, bytes)
                        else str(key).replace(f"tool:{toolset_name}:", "")
                    )
                    all_tools.append(tool_name)
            else:
                # Handle single key case
                tool_name = (
                    tool_keys.decode().replace(f"tool:{toolset_name}:", "")
                    if isinstance(tool_keys, bytes)
                    else str(tool_keys).replace(f"tool:{toolset_name}:", "")
                )
                all_tools.append(tool_name)

        # Apply pagination
        total_tools = len(all_tools)
        total_pages = max(1, (total_tools + page_size - 1) // page_size)
        page = min(max(1, page), total_pages)  # Ensure page is within bounds

        # Get paginated subset of tools
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_tools)
        paginated_tools = all_tools[start_idx:end_idx]

        # Get metadata for each tool in the current page
        tools_info = []
        for tool_name in paginated_tools:
            # Get tool metadata
            tool_metadata_raw = safe_redis_result(
                redis_client.get(f"tool:{toolset_name}:{tool_name}")
            )
            tool_metadata = {}

            if tool_metadata_raw:
                import json

                try:
                    if isinstance(tool_metadata_raw, bytes):
                        tool_metadata = json.loads(tool_metadata_raw.decode())
                    else:
                        tool_metadata = json.loads(tool_metadata_raw)
                except json.JSONDecodeError:
                    tool_metadata = {"error": "Could not parse tool metadata"}

            tools_info.append({"name": tool_name, "metadata": tool_metadata})

        return {
            "toolset": toolset_name,
            "items": tools_info,
            "total": total_tools,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tools for toolset {toolset_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving toolset tools: {str(e)}"
        )


@router.get("/toolsets/{toolset_name}")
async def get_toolset_details(toolset_name: str):
    """Get summary information about a specific toolset without listing all tools"""
    try:
        # Check if toolset exists in Redis
        redis_client = RedisCompatibleCache.get_redis_client()
        toolset_exists = bool(
            safe_redis_result(redis_client.exists(f"cache_registry:{toolset_name}"))
        )

        if not toolset_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Toolset '{toolset_name}' not found in Redis registry",
            )

        # Count how many tools are in this toolset
        tool_keys = safe_redis_result(redis_client.keys(f"tool:{toolset_name}:*"))
        tool_count = (
            len(tool_keys) if isinstance(tool_keys, list) else 1 if tool_keys else 0
        )

        # Get toolset metadata from Redis
        is_deterministic_raw = safe_redis_result(
            redis_client.get(f"cache_meta:{toolset_name}:deterministic")
        )
        is_deterministic = False
        if is_deterministic_raw:
            is_deterministic = (
                bool(int(is_deterministic_raw.decode()))
                if isinstance(is_deterministic_raw, bytes)
                else bool(int(is_deterministic_raw))
            )

        expiry_raw = safe_redis_result(
            redis_client.get(f"cache_meta:{toolset_name}:expiry")
        )
        expiry = 3600
        if expiry_raw:
            expiry = (
                int(expiry_raw.decode())
                if isinstance(expiry_raw, bytes)
                else int(expiry_raw)
            )

        # Get cache statistics
        cache = RedisCompatibleCache.get_cache_for_tool(toolset_name)
        cache_stats = cache.get_stats()

        return {
            "name": toolset_name,
            "deterministic": is_deterministic,
            "expiry_seconds": None if is_deterministic else expiry,
            "tools_count": tool_count,
            "cache_stats": cache_stats,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting toolset details for {toolset_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving toolset details: {str(e)}"
        )


@router.get("/toolsets/{toolset_name}/tools/{tool_name}")
async def get_tool_details(toolset_name: str, tool_name: str):
    """Get detailed information about a specific tool"""
    try:
        # Check if toolset exists in Redis
        redis_client = RedisCompatibleCache.get_redis_client()
        toolset_exists = bool(
            safe_redis_result(redis_client.exists(f"cache_registry:{toolset_name}"))
        )

        if not toolset_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Toolset '{toolset_name}' not found in Redis registry",
            )

        # Check if tool exists
        tool_exists = bool(
            safe_redis_result(redis_client.exists(f"tool:{toolset_name}:{tool_name}"))
        )

        if not tool_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found in toolset '{toolset_name}'",
            )

        # Get tool metadata
        tool_metadata_raw = safe_redis_result(
            redis_client.get(f"tool:{toolset_name}:{tool_name}")
        )
        tool_metadata = {}

        if tool_metadata_raw:
            import json

            try:
                if isinstance(tool_metadata_raw, bytes):
                    tool_metadata = json.loads(tool_metadata_raw.decode())
                else:
                    tool_metadata = json.loads(tool_metadata_raw)
            except json.JSONDecodeError:
                tool_metadata = {"error": "Could not parse tool metadata"}

        return {"toolset": toolset_name, "name": tool_name, "metadata": tool_metadata}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool details for {toolset_name}/{tool_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving tool details: {str(e)}"
        )


@router.get("/cache/list")
async def list_caches():
    """List all available caches from Redis registry"""
    try:
        # Get Redis client to find all registered caches
        redis_client = RedisCompatibleCache.get_redis_client()
        cache_registry_keys = safe_redis_result(redis_client.keys("cache_registry:*"))

        # Convert to list of cache names
        all_cache_names = []
        if cache_registry_keys:
            if isinstance(cache_registry_keys, list):
                for key in cache_registry_keys:
                    cache_name = (
                        key.decode().replace("cache_registry:", "")
                        if isinstance(key, bytes)
                        else str(key).replace("cache_registry:", "")
                    )
                    all_cache_names.append(cache_name)
            else:
                # Handle single key case
                cache_name = (
                    cache_registry_keys.decode().replace("cache_registry:", "")
                    if isinstance(cache_registry_keys, bytes)
                    else str(cache_registry_keys).replace("cache_registry:", "")
                )
                all_cache_names.append(cache_name)

        # Get details for each cache
        cache_details = []
        for name in all_cache_names:
            # Get cache metadata from Redis
            is_deterministic_raw = safe_redis_result(
                redis_client.get(f"cache_meta:{name}:deterministic")
            )
            is_deterministic = False
            if is_deterministic_raw:
                is_deterministic = (
                    bool(int(is_deterministic_raw.decode()))
                    if isinstance(is_deterministic_raw, bytes)
                    else bool(int(is_deterministic_raw))
                )

            expiry_raw = safe_redis_result(
                redis_client.get(f"cache_meta:{name}:expiry")
            )
            expiry = 3600
            if expiry_raw:
                expiry = (
                    int(expiry_raw.decode())
                    if isinstance(expiry_raw, bytes)
                    else int(expiry_raw)
                )

            cache_details.append(
                {
                    "name": name,
                    "deterministic": is_deterministic,
                    "expiry_seconds": None if is_deterministic else expiry,
                }
            )

        return {"caches": cache_details, "total": len(cache_details)}
    except Exception as e:
        logger.error(f"Error listing caches: {e}")
        return {"error": str(e), "caches": [], "total": 0}


@router.get("/caches/debug")
async def debug_caches():
    """Diagnostic endpoint for cache debugging"""
    try:
        # Force discovery of caches
        discovered = discover_toolsets()

        # Get Redis client to find all registered caches
        redis_client = RedisCompatibleCache.get_redis_client()
        cache_registry_keys = safe_redis_result(redis_client.keys("cache_registry:*"))

        # Convert to list of cache names
        redis_caches = []
        if cache_registry_keys:
            if isinstance(cache_registry_keys, list):
                for key in cache_registry_keys:
                    cache_name = (
                        key.decode().replace("cache_registry:", "")
                        if isinstance(key, bytes)
                        else str(key).replace("cache_registry:", "")
                    )
                    redis_caches.append(cache_name)
            else:
                # Handle single key case
                cache_name = (
                    cache_registry_keys.decode().replace("cache_registry:", "")
                    if isinstance(cache_registry_keys, bytes)
                    else str(cache_registry_keys).replace("cache_registry:", "")
                )
                redis_caches.append(cache_name)

        # Collect cache info
        cache_info = {}
        for name in redis_caches:
            try:
                # Get or create cache instance
                cache = RedisCompatibleCache.get_cache_for_tool(name)
                stats = cache.get_stats()

                # Count entries and references in Redis
                cache_entries = len(
                    safe_redis_result(redis_client.keys(f"cache:{name}:*")) or []
                )
                registry_entries = len(
                    safe_redis_result(redis_client.keys(f"registry:{name}:*")) or []
                )

                # Get metadata from Redis
                is_deterministic_raw = safe_redis_result(
                    redis_client.get(f"cache_meta:{name}:deterministic")
                )
                is_deterministic = False
                if is_deterministic_raw:
                    is_deterministic = (
                        bool(int(is_deterministic_raw.decode()))
                        if isinstance(is_deterministic_raw, bytes)
                        else bool(int(is_deterministic_raw))
                    )

                expiry_raw = safe_redis_result(
                    redis_client.get(f"cache_meta:{name}:expiry")
                )
                expiry = 3600
                if expiry_raw:
                    expiry = (
                        int(expiry_raw.decode())
                        if isinstance(expiry_raw, bytes)
                        else int(expiry_raw)
                    )
                if is_deterministic:
                    expiry = None

                cache_info[name] = {
                    "stats": stats,
                    "entries": cache_entries,
                    "references": registry_entries,
                    "deterministic": is_deterministic,
                    "expiry": expiry,
                }
            except Exception as e:
                cache_info[name] = {"error": str(e)}

        return {
            "discovered_toolsets": discovered,
            "redis_caches": redis_caches,
            "local_registry": list(ToolsetCache._cache_registry.keys()),
            "caches": cache_info,
            "environment": {
                "MCP_CACHES_INITIALIZED": os.environ.get("MCP_CACHES_INITIALIZED"),
                "MCP_USE_EXISTING_CACHES": os.environ.get("MCP_USE_EXISTING_CACHES"),
                "ER_CACHE_BASE": settings.er_cache_url,
            },
        }
    except Exception as e:
        logger.error(f"Error in debug_caches: {e}")
        return {"error": str(e)}


@router.get("/cache/stats")
async def get_all_cache_stats():
    """Get statistics for all caches, including those stored in Redis"""
    try:
        # Get Redis client to find all registered caches
        redis_client = RedisCompatibleCache.get_redis_client()
        cache_registry_keys = safe_redis_result(redis_client.keys("cache_registry:*"))

        # Convert to list of cache names
        all_cache_names = []
        if cache_registry_keys:
            if isinstance(cache_registry_keys, list):
                for key in cache_registry_keys:
                    cache_name = (
                        key.decode().replace("cache_registry:", "")
                        if isinstance(key, bytes)
                        else str(key).replace("cache_registry:", "")
                    )
                    all_cache_names.append(cache_name)
            else:
                # Handle single key case
                cache_name = (
                    cache_registry_keys.decode().replace("cache_registry:", "")
                    if isinstance(cache_registry_keys, bytes)
                    else str(cache_registry_keys).replace("cache_registry:", "")
                )
                all_cache_names.append(cache_name)

        # Get stats for each cache
        stats = {}
        for name in all_cache_names:
            # Get or create cache instance
            cache = RedisCompatibleCache.get_cache_for_tool(name)
            stats[name] = cache.get_stats()

        return {"caches": stats, "total_caches": len(stats)}
    except Exception as e:
        logger.error(f"Error getting all cache stats: {e}")
        return {"error": str(e), "caches": {}, "total_caches": 0}


@router.get("/cache/stats/{cache_name}")
async def get_cache_stats(cache_name: str):
    """Get statistics for a specific cache"""
    try:
        # Check if cache exists in Redis
        redis_client = RedisCompatibleCache.get_redis_client()
        cache_exists = bool(
            safe_redis_result(redis_client.exists(f"cache_registry:{cache_name}"))
        )

        if not cache_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Cache '{cache_name}' not found in Redis registry",
            )

        # Get or create cache instance
        cache = RedisCompatibleCache.get_cache_for_tool(cache_name)
        return cache.get_stats()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache stats for {cache_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving cache stats: {str(e)}"
        )


@router.get("/cache/inspect/{cache_name}")
async def inspect_cache(cache_name: str):
    """Inspect contents of a specific cache"""
    try:
        # Check if cache exists in Redis
        redis_client = RedisCompatibleCache.get_redis_client()
        cache_exists = bool(
            safe_redis_result(redis_client.exists(f"cache_registry:{cache_name}"))
        )

        if not cache_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Cache '{cache_name}' not found in Redis registry",
            )

        # Get or create cache instance
        cache = RedisCompatibleCache.get_cache_for_tool(cache_name)
        return cache.inspect_cache()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inspecting cache {cache_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error inspecting cache: {str(e)}")


@router.post("/cache/flush/{cache_name}")
async def flush_cache(cache_name: str):
    """Flush a specific cache to disk (if deterministic)"""
    try:
        # Check if cache exists in Redis
        redis_client = RedisCompatibleCache.get_redis_client()
        cache_exists = bool(
            safe_redis_result(redis_client.exists(f"cache_registry:{cache_name}"))
        )

        if not cache_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Cache '{cache_name}' not found in Redis registry",
            )

        # Get cache instance
        cache = RedisCompatibleCache.get_cache_for_tool(cache_name)

        # Check if it's deterministic
        is_deterministic_raw = safe_redis_result(
            redis_client.get(f"cache_meta:{cache_name}:deterministic")
        )
        is_deterministic = False
        if is_deterministic_raw:
            is_deterministic = (
                bool(int(is_deterministic_raw.decode()))
                if isinstance(is_deterministic_raw, bytes)
                else bool(int(is_deterministic_raw))
            )

        if not is_deterministic:
            return {"status": "skipped", "reason": "Cache is not deterministic"}

        # Flush the cache
        cache.flush()
        return {"status": "success", "message": f"Cache '{cache_name}' flushed to disk"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error flushing cache {cache_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error flushing cache: {str(e)}")


@router.post("/cache/clear/{cache_name}")
async def clear_cache(cache_name: str):
    """Clear all entries from a specific cache"""
    try:
        # Check if cache exists in Redis
        redis_client = RedisCompatibleCache.get_redis_client()
        cache_exists = bool(
            safe_redis_result(redis_client.exists(f"cache_registry:{cache_name}"))
        )

        if not cache_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Cache '{cache_name}' not found in Redis registry",
            )

        # Get cache instance
        cache = RedisCompatibleCache.get_cache_for_tool(cache_name)
        count = cache.clear()

        return {"status": "success", "cleared_entries": count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cache {cache_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")
