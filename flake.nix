{
  description = "oap-langgraph-tools-agent - A pre-built LangGraph tools agent for Open Agent Platform with MCP servers and a LangConnect RAG tool.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (
      system: let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        fhsEnv = pkgs.buildFHSEnv {
          name = "oap-langgraph-tools-agent-dev-env";

          targetPkgs = pkgs':
            with pkgs'; [
              # Python and uv
              python312
              uv

              # System libraries (required for some dependencies)
              zlib
              stdenv.cc.cc.lib

              # Playwright / Chromium runtime libraries
              # Needed for running the downloaded Playwright Chromium binaries inside the FHS env.
              expat
              glib
              mesa
              libdrm
              libglvnd
              systemd
              nss
              nspr
              atk
              at-spi2-atk
              cups
              libdrm
              libxkbcommon
              mesa
              pango
              cairo
              alsa-lib
              dbus
              xorg.libX11
              xorg.libXcomposite
              xorg.libXdamage
              xorg.libXext
              xorg.libXfixes
              xorg.libXrandr
              xorg.libxcb
              xorg.libxshmfence
              xorg.libXi
              xorg.libXtst

              # Shells
              zsh
              bash

              # Linting & Formatting
              ruff
              pre-commit

              # Development tools
              git
              git-lfs
              curl
              wget
              jq
              tree
              httpie
            ];

          profile = ''
            echo "🚀 oap-langgraph-tools-agent Development Environment"
            echo "==========================================="

            # Create and activate uv virtual environment if it doesn't exist
            if [ ! -d ".venv" ]; then
              echo "📦 Creating uv virtual environment..."
              uv venv --python python3.12 --prompt "oap-langgraph-tools-agent"
            fi

            # Activate the virtual environment
            source .venv/bin/activate

            # Set a recognizable name for IDEs
            export VIRTUAL_ENV_PROMPT="oap-langgraph-tools-agent"

            # Sync dependencies
            if [ -f "pyproject.toml" ]; then
              echo "🔄 Syncing dependencies..."
              uv sync --quiet
            else
              echo "⚠️  No pyproject.toml found. Run 'uv init' to create project."
            fi

            echo ""
            echo "✅ Python: $(python --version)"
            echo "✅ uv:     $(uv --version)"
            echo "✅ Virtual environment: activated (.venv)"
            echo "✅ PYTHONPATH: $PWD/src:$PWD"
          '';

          runScript = ''
            # Set shell for the environment
            SHELL=${pkgs.zsh}/bin/zsh

            # Set PYTHONPATH to project root for module imports
            export PYTHONPATH="$PWD/src:$PWD"
            export SSL_CERT_FILE="/etc/ssl/certs/ca-bundle.crt"

            # Playwright Chromium (downloaded binary) can fail to start if it picks up a
            # 32-bit libgbm (ELFCLASS32) or can't resolve libgbm.so.1. In this FHS env,
            # the robust fix is to ensure the FHS rootfs /usr/lib64 is *ahead* of other
            # library search paths.
            #
            # This finds the rootfs for this FHS env at runtime and prepends its usr/lib64.
            fhs_usr_lib64="$(ls -d /nix/store/*-oap-langgraph-tools-agent-dev-env-fhsenv-rootfs/usr/lib64 2>/dev/null | head -n 1)"

            # Playwright Chromium needs libgbm.so.1. Depending on the pinned nixpkgs,
            # the providing attribute name can vary, but the store path typically
            # contains a '*-mesa-libgbm-*' derivation. We locate it at runtime and
            # prepend its /lib directory if present.
            mesa_libgbm_lib="$(ls -d /nix/store/*-mesa-libgbm-*/lib 2>/dev/null | head -n 1)"

            if [ -z "$mesa_libgbm_lib" ]; then
              echo "⚠️  Playwright/Chromium: could not locate a '*-mesa-libgbm-*' store path."
              echo "    Chromium may fail with: libgbm.so.1: cannot open shared object file"
              echo "    Workaround: set LD_LIBRARY_PATH to include the correct mesa-libgbm /lib path."
            fi

            if [ -n "$fhs_usr_lib64" ]; then
              export LD_LIBRARY_PATH="$fhs_usr_lib64:''${mesa_libgbm_lib:+$mesa_libgbm_lib:}${pkgs.mesa}/lib:${pkgs.libdrm}/lib:${pkgs.systemd}/lib:${pkgs.libglvnd}/lib:${pkgs.glib}/lib:${pkgs.expat}/lib:''${LD_LIBRARY_PATH:-}"
            else
              export LD_LIBRARY_PATH="''${mesa_libgbm_lib:+$mesa_libgbm_lib:}${pkgs.mesa}/lib:${pkgs.libdrm}/lib:${pkgs.systemd}/lib:${pkgs.libglvnd}/lib:${pkgs.glib}/lib:${pkgs.expat}/lib:''${LD_LIBRARY_PATH:-}"
            fi

            echo ""
            echo "🚀 oap-langgraph-tools-agent Quick Reference:"
            echo ""
            echo "🔧 Development:"
            echo "  uv sync                    - Sync dependencies"
            echo "  uv run pytest              - Run tests"
            echo "  uv run ruff check .        - Lint code"
            echo "  uv run ruff format .       - Format code"
            echo "  uv lock --upgrade          - Update all dependencies"
            echo ""
            echo "📦 Package Management:"
            echo "  uv add <package>           - Add runtime dependency"
            echo "  uv add --dev <package>     - Add dev dependency"
            echo "  uv remove <package>        - Remove dependency"
            echo ""
            echo "🚀 Run Server:"
            echo "  uv run langgraph dev --no-browser     - Run LangGraph dev server (recommended)"
            echo ""
            echo "🔗 Notes:"
            echo "  This repository is a fork/variant of the LangChain agent runtime for OAP."
            echo ""
            echo "🚀 Ready to build!"
            echo ""

            # Start zsh shell
            exec ${pkgs.zsh}/bin/zsh
          '';
        };
      in {
        devShells.default = pkgs.mkShell {
          shellHook = ''
            exec ${fhsEnv}/bin/oap-langgraph-tools-agent-dev-env
          '';
        };

        packages.default = pkgs.python312;
      }
    );
}
