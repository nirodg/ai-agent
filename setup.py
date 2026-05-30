#!/usr/bin/env python3
"""
setup.py — First-time project setup for the AI Sales Enrichment Agent.
Run once after cloning: python setup.py
"""

import subprocess
import sys
from getpass import getpass
from pathlib import Path


def run(cmd: list[str], check: bool = True):
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, check=check)


def _looks_like_placeholder(value: str) -> bool:
    v = (value or "").strip().lower()
    if not v:
        return True
    markers = ("your_", "example", "changeme", "replace_me", "sk-proj-your", "pplx-your", "ollama-your")
    return any(m in v for m in markers)


def _warn_placeholder_api_keys(env_path: Path):
    key_values = {}
    for ln in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(ln)
        if parsed:
            k, v = parsed
            if "API_KEY" in k:
                key_values[k] = v

    bad = [k for k, v in key_values.items() if _looks_like_placeholder(v)]
    if bad:
        print("\n⚠️  Some API keys look empty or placeholder values:")
        for k in bad:
            print(f"  - {k}")
        print("  Setup will continue, but API calls may fail until these are updated.")


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        return None
    key, value = line.split("=", 1)
    return key.strip(), value.rstrip("\n")


def _build_env_from_example(example_path: Path, env_path: Path):
    if not example_path.exists():
        raise FileNotFoundError(f"Missing template file: {example_path}")

    existing = {}
    if env_path.exists():
        for ln in env_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(ln)
            if parsed:
                k, v = parsed
                existing[k] = v

    result_lines: list[str] = []
    print("\n🔑 Configure environment (.env) from .env.example")

    for raw_line in example_path.read_text(encoding="utf-8").splitlines(keepends=True):
        parsed = _parse_env_line(raw_line)
        if not parsed:
            result_lines.append(raw_line)
            continue

        key, default_value = parsed
        current_value = existing.get(key, default_value)
        should_prompt_secret = ("KEY" in key) or ("TOKEN" in key)

        if should_prompt_secret:
            masked_hint = "(currently set)" if current_value and "your_" not in current_value else "(empty)"
            user_value = getpass(f"  {key} {masked_hint}: ").strip()
            final_value = user_value if user_value else current_value
        else:
            user_value = input(f"  {key} [{current_value}]: ").strip()
            final_value = user_value if user_value else current_value

        result_lines.append(f"{key}={final_value}\n")

    env_path.write_text("".join(result_lines), encoding="utf-8")
    print("✅ .env generated from .env.example")
    _warn_placeholder_api_keys(env_path)


def main():
    print("\n🚀 AI Sales Enrichment Agent — Setup\n")

    # 1. Check Python version
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        print(f"❌ Python 3.11+ required (found {major}.{minor}). Aborting.")
        sys.exit(1)
    print(f"✅ Python {major}.{minor} detected")

    # 2. Create virtualenv if not already inside one
    in_venv = sys.prefix != sys.base_prefix
    venv_dir = Path(".venv")
    if not in_venv:
        if not venv_dir.exists():
            print("\n📦 Creating virtual environment (.venv)…")
            run([sys.executable, "-m", "venv", str(venv_dir)])
        else:
            print("\n📦 Virtual environment (.venv) already exists")

        # Point pip/python to the venv
        if sys.platform == "win32":
            pip = str(venv_dir / "Scripts" / "pip.exe")
        else:
            pip = str(venv_dir / "bin" / "pip")
    else:
        print("✅ Already inside a virtual environment")
        pip = str(Path(sys.executable).with_name("pip"))

    # 3. Upgrade pip
    print("\n⬆️  Upgrading pip…")
    run([pip, "install", "--upgrade", "pip"], check=False)

    # 4. Install dependencies
    print("\n📥 Installing dependencies from requirements.txt…")
    run([pip, "install", "-r", "requirements.txt"])

    # 5. Create/update .env from .env.example
    env_file = Path(".env")
    env_example = Path(".env.example")
    if not sys.stdin.isatty():
        print("\n⚠️  Non-interactive terminal detected.")
        if not env_file.exists():
            print("  ❌ .env is missing and interactive setup is unavailable.")
            print("  Create .env from .env.example before running in non-interactive mode.")
            sys.exit(1)
        else:
            print("✅ .env already exists (skipping interactive setup)")
            _warn_placeholder_api_keys(env_file)
    else:
        if not env_example.exists():
            print("\n❌ .env.example not found; cannot build .env template.")
            sys.exit(1)
        if env_file.exists():
            overwrite = input("\n🧩 .env already exists. Reconfigure from .env.example? [y/N]: ").strip().lower()
            if overwrite == "y":
                _build_env_from_example(env_example, env_file)
            else:
                print("✅ Keeping existing .env")
                _warn_placeholder_api_keys(env_file)
        else:
            _build_env_from_example(env_example, env_file)

    # 6. Done
    print("\n✅ Setup complete!\n")
    if sys.platform == "win32":
        activate = r".venv\Scripts\activate"
        run_cmd  = "run.bat"
    else:
        activate = "source .venv/bin/activate"
        run_cmd  = "./run.sh"

    if not in_venv:
        print(f"Next steps:")
        print(f"  1. Review .env values")
        print(f"  2. {activate}")
        print(f"  3. {run_cmd}   (or: python -m streamlit run main.py)\n")
    else:
        print(f"Next steps:")
        print(f"  1. Review .env values")
        print(f"  2. {run_cmd}   (or: python -m streamlit run main.py)\n")


if __name__ == "__main__":
    main()