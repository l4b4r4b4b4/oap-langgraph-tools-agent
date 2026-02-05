from fastapi import APIRouter
import logging
import platform
import subprocess

router = APIRouter(prefix="/api/v1/system_0", tags=["System 0 | Operating environment"])
logger = logging.getLogger(__name__)


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


@router.get("/debug/compute")
async def debug_compute():
    """Get detailed information about available compute capabilities"""
    try:
        compute_info = get_compute_capabilities()

        # Add nvidia-smi output if available
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
            nvidia_smi = (
                result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
            )
            compute_info["nvidia_smi"] = nvidia_smi
            compute_info["nvidia_smi_status"] = (
                "OK" if result.returncode == 0 else "Failed"
            )
        except Exception as e:
            compute_info["nvidia_smi_error"] = str(e)

        # Check if libraries are available
        try:
            import ctypes

            cuda_libraries = []
            for lib in ["libcuda.so.1", "libcudart.so", "libnvidia-ml.so.1"]:
                try:
                    ctypes.CDLL(lib)
                    cuda_libraries.append({"name": lib, "status": "loaded"})
                except Exception as e:
                    cuda_libraries.append(
                        {"name": lib, "status": "failed", "error": str(e)}
                    )
            compute_info["cuda_libraries"] = cuda_libraries
        except Exception as e:
            compute_info["cuda_libraries_error"] = str(e)

        return compute_info
    except Exception as e:
        logger.error(f"Error in debug_compute: {e}")
        return {"error": str(e)}
