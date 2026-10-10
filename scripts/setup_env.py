"""Install into the active Python 3.12 environment; never silently replace Isaac Sim."""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "28a37cecdd433c22d9eabd6a5954add9f13a8951"
PACKAGES = ["isaaclab", "isaaclab_assets", "isaaclab_contrib", "isaaclab_experimental",
            "isaaclab_newton", "isaaclab_ov", "isaaclab_ovphysx", "isaaclab_physx",
            "isaaclab_rl", "isaaclab_tasks", "isaaclab_visualizers"]


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--install-isaacsim", action="store_true",
                        help="Install the cloud version 6.0.0.1 if missing. Requires acceptance of NVIDIA's terms.")
    parser.add_argument("--isaaclab", type=Path, help="Existing checkout at the exact pinned commit.")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use a Python 3.12 virtual environment for this snapshot.")
    try:
        sim_version = metadata.version("isaacsim")
    except metadata.PackageNotFoundError:
        if not args.install_isaacsim:
            raise RuntimeError("Install Isaac Sim 6.0.0.1 first, or pass --install-isaacsim after accepting NVIDIA's terms.")
        run(sys.executable, "-m", "pip", "install", "isaacsim[all,extscache]==6.0.0.1",
            "--extra-index-url", "https://pypi.nvidia.com")
        sim_version = metadata.version("isaacsim")
    if sim_version != "6.0.0.1":
        raise RuntimeError(f"Expected Isaac Sim 6.0.0.1, found {sim_version}. Create a separate environment.")
    lab = args.isaaclab.resolve() if args.isaaclab else ROOT / "dependencies/IsaacLab"
    if not (lab / ".git").exists():
        if args.isaaclab:
            raise RuntimeError("--isaaclab must point to a Git checkout.")
        lab.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", "--filter=blob:none", "--no-checkout", "https://github.com/isaac-sim/IsaacLab.git", lab)
        run("git", "-C", lab, "fetch", "--depth=1", "origin", COMMIT)
        run("git", "-C", lab, "checkout", "--detach", COMMIT)
    actual = subprocess.check_output(["git", "-C", str(lab), "rev-parse", "HEAD"], text=True).strip()
    if actual != COMMIT:
        raise RuntimeError(f"IsaacLab checkout mismatch: {actual}; expected {COMMIT}. Existing checkout was not changed.")
    run(sys.executable, "-m", "pip", "install", "setuptools<81", "wheel", "toml")
    editable = []
    for package in PACKAGES:
        editable += ["-e", str(lab / "source" / package)]
    run(sys.executable, "-m", "pip", "install", *editable,
        "-e", ROOT / "legged_lab/source/legged_lab", "-r", ROOT / "environment/requirements-runtime.txt",
        "--extra-index-url", "https://pypi.nvidia.com")
    settings = ROOT / "legged_lab/.vscode/settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"python.defaultInterpreterPath": sys.executable,
                                   "python.analysis.extraPaths": [str(lab / "source")]}, indent=2))
    print("Installation complete. Run: python scripts/repro.py verify")
    print("Then: python scripts/repro.py play --num-envs 1 --viz kit")


if __name__ == "__main__":
    main()
