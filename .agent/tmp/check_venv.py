#!/usr/bin/env python3
"""
Check what gets installed in virtual environment for oap-langgraph-tools-agent.
Specifically check if langgraph CLI is available and where it comes from.
"""

import os
import sys
import subprocess
import tempfile


def main():
    print("🔍 Checking virtual environment installation")
    print("=" * 60)

    # Get project root
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    print(f"Project root: {project_root}")

    # Check pyproject.toml
    pyproject_path = os.path.join(project_root, "pyproject.toml")
    if not os.path.exists(pyproject_path):
        print(f"❌ pyproject.toml not found at {pyproject_path}")
        return 1

    print("✅ Found pyproject.toml")

    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = os.path.join(tmpdir, "venv")

        print(f"\n1. Creating virtual environment at {venv_path}")
        # Create venv using current python
        result = subprocess.run(
            [sys.executable, "-m", "venv", venv_path], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to create venv: {result.stderr}")
            return 1
        print("✅ Virtual environment created")

        # Get pip path
        pip_path = os.path.join(venv_path, "bin", "pip")
        if sys.platform == "win32":
            pip_path = os.path.join(venv_path, "Scripts", "pip.exe")

        print("\n2. Installing package in development mode")
        result = subprocess.run(
            [pip_path, "install", "-e", project_root], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to install package: {result.stderr}")
            return 1
        print("✅ Package installed")

        print("\n3. Listing installed packages")
        result = subprocess.run(
            [pip_path, "list"], capture_output=True, text=True, check=True
        )
        print("Installed packages:")
        for line in result.stdout.split("\n"):
            if any(
                pkg in line.lower() for pkg in ["langgraph", "langchain", "tools-agent"]
            ):
                print(f"  {line}")

        print("\n4. Checking for langgraph CLI")
        # Check bin directory
        bin_dir = os.path.join(venv_path, "bin")
        if sys.platform == "win32":
            bin_dir = os.path.join(venv_path, "Scripts")

        if not os.path.exists(bin_dir):
            print(f"❌ Bin directory not found: {bin_dir}")
            return 1

        print(f"Checking {bin_dir}:")
        langgraph_found = False
        for item in os.listdir(bin_dir):
            item_path = os.path.join(bin_dir, item)
            if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                if "langgraph" in item.lower():
                    langgraph_found = True
                    print(f"  ✅ Found: {item}")
                    # Check what package it comes from
                    try:
                        result = subprocess.run(
                            [pip_path, "show", "-f", "langgraph-cli"],
                            capture_output=True,
                            text=True,
                        )
                        if result.returncode == 0:
                            print("     Comes from: langgraph-cli")
                    except:
                        pass

        if not langgraph_found:
            print("  ❌ langgraph CLI not found in bin directory")

            # Check if langgraph-cli is installed
            result = subprocess.run(
                [pip_path, "show", "langgraph-cli"], capture_output=True, text=True
            )
            if result.returncode == 0:
                print("  ℹ️  langgraph-cli is installed but no CLI found")
                print("  Package info:")
                for line in result.stdout.split("\n")[:10]:
                    if line.strip():
                        print(f"    {line}")
            else:
                print("  ℹ️  langgraph-cli is NOT installed")

                # Check dependencies
                print("\n5. Checking dependencies in pyproject.toml")
                with open(pyproject_path, "r") as f:
                    content = f.read()
                    if "langgraph-cli" in content:
                        print("  ✅ langgraph-cli found in pyproject.toml")
                        # Check if it's dev dependency
                        if "dependency-groups" in content and "dev" in content:
                            dev_start = content.find("[dependency-groups.dev]")
                            if dev_start != -1:
                                dev_section = content[dev_start:]
                                if "langgraph-cli" in dev_section:
                                    print("  ℹ️  langgraph-cli is a DEV dependency")
                                    print(
                                        "  ⚠️  Will not be installed with --no-dev flag"
                                    )
                    else:
                        print("  ❌ langgraph-cli not in pyproject.toml")

        print("\n6. Testing installation with --no-dev flag (like Dockerfile)")
        # Clean and reinstall with --no-dev
        subprocess.run(
            [pip_path, "uninstall", "-y", "tools-agent"], capture_output=True
        )

        # Install without dev dependencies
        result = subprocess.run(
            [pip_path, "install", "--no-deps", "-e", project_root],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✅ Installed without dev dependencies")

            # Check for langgraph again
            langgraph_still_found = False
            for item in os.listdir(bin_dir):
                if "langgraph" in item.lower():
                    langgraph_still_found = True
                    print(f"  ℹ️  langgraph CLI still present: {item}")

            if not langgraph_still_found:
                print("  ✅ langgraph CLI correctly not present with --no-dev")
                print("\n⚠️  CONCLUSION: Dockerfile needs adjustment")
                print("   langgraph CLI comes from langgraph-cli (dev dependency)")
                print("   Options:")
                print("   1. Install dev dependencies in Docker")
                print("   2. Use different command to start server")
                print("   3. Make langgraph-cli a runtime dependency")
        else:
            print(f"❌ Failed to install without dev dependencies: {result.stderr}")

    print("\n" + "=" * 60)
    print("📋 CHECK COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
