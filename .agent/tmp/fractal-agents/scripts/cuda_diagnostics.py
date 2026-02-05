import sys
import platform

def print_header(title):
    print("\n" + "=" * 40)
    print(f" {title}")
    print("=" * 40)

def main():
    print_header("SYSTEM INFORMATION")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Processor: {platform.processor()}")

    try:
        # Check for CUDA with PyTorch
        print_header("PYTORCH CUDA CHECK")
        try:
            import torch
            print(f"PyTorch version: {torch.__version__}")
            print(f"CUDA available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                print(f"CUDA version: {torch.version.cuda}")
                print(f"CUDA device count: {torch.cuda.device_count()}")
                for i in range(torch.cuda.device_count()):
                    print(f"  Device {i}: {torch.cuda.get_device_name(i)}")
            else:
                print("CUDA is not available with PyTorch")
        except ImportError:
            print("PyTorch is not installed")

    except Exception as e:
        print(f"Error during diagnostics: {e}")

if __name__ == "__main__":
    main()
