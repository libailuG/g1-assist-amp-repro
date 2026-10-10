"""Portable launcher: python scripts/repro.py play|train|smoke|verify."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "legged_lab"
TASK = "LeggedLab-Isaac-AMP-Rough-G1-Assist"
MODEL = PROJECT / "source/legged_lab/legged_lab/data/Robots/Unitree/g1_29dof_assist/usd/g1_29dof_assist_v1"
CHECKPOINT = ROOT / "checkpoints/model_14800.pt"


def verify():
    manifest = json.loads((ROOT / "environment/SHA256SUMS.json").read_text())
    for name, expected in manifest.items():
        path = ROOT / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Checksum mismatch: {name}")
    print(f"Verified {len(manifest)} source, model, checkpoint and record files.")


def display_model():
    """Remove only unresolved references to absent sensor visuals in a copy."""
    from pxr import Usd
    target = ROOT / "generated/play-model"
    shutil.copytree(MODEL, target, dirs_exist_ok=True)
    stage = Usd.Stage.Open(str(target / "configuration/g1_29dof_assist_base.usd"))
    for name in ("imu_in_pelvis", "imu_in_torso", "d435_link", "mid360_link"):
        prim = stage.GetPrimAtPath(f"/g1_29dof_assist/{name}/visuals")
        if not prim.IsValid():
            raise RuntimeError(f"Missing expected visual prim: {name}")
        prim.GetReferences().ClearReferences()
    stage.GetRootLayer().Save()
    entry = target / "g1_29dof_assist.usd"
    if Usd.Stage.Open(str(entry)).GetCompositionErrors():
        raise RuntimeError("Display USD still has composition errors.")
    return entry


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=["verify", "play", "train", "smoke"])
    parser.add_argument("--num-envs", type=int)
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--viz", choices=["kit", "viser"], default="kit")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    parser.add_argument("--no-real-time", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args, extras = parser.parse_known_args()
    if args.command == "verify":
        verify()
        return 0
    train = args.command in ("train", "smoke")
    count = args.num_envs if args.num_envs is not None else (64 if args.command == "smoke" else 8192 if train else 4)
    iterations = args.iterations if args.iterations is not None else (3 if args.command == "smoke" else 30000)
    if count < 1 or iterations < 1:
        parser.error("Environment and iteration counts must be positive.")
    cmd = [sys.executable, "scripts/rsl_rl/train.py" if train else "scripts/rsl_rl/play.py",
           "--task", TASK + ("-v0" if train else "-Play-v0"), "--num_envs", str(count),
           "--seed", str(args.seed), "--device", args.device, f"agent.device={args.device}"]
    if train:
        cmd += ["--headless", "--max_iterations", str(iterations), "--logger", "tensorboard",
                "--run_name", f"repro_{count}_pd_1ms" + ("_smoke" if args.command == "smoke" else ""),
                "agent.resume=false", "agent.save_interval=200"]
    else:
        checkpoint = args.checkpoint.resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
        cmd += ["--checkpoint", str(checkpoint), "--viz", args.viz, "--follow_cam"]
        if not args.no_real_time:
            cmd += ["--real-time"]
        entry = MODEL / "g1_29dof_assist.usd" if args.dry_run else display_model()
        cmd += [f"env.scene.robot.spawn.usd_path={entry.as_posix()}"]
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd += ["--kit_args=--allow-root"]
    cmd += extras
    print("Working directory:", PROJECT, flush=True)
    print("Command:", subprocess.list2cmdline(cmd), flush=True)
    if args.dry_run:
        return 0
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    environment.setdefault("OMP_NUM_THREADS", "4")
    source = str(PROJECT / "source/legged_lab")
    environment["PYTHONPATH"] = source + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
    # EULA acceptance is handled by the user during Isaac Sim installation.
    output_dir = ROOT / "generated"
    output_dir.mkdir(exist_ok=True)
    failed = False
    process = subprocess.Popen(cmd, cwd=PROJECT, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1)
    try:
        with (output_dir / f"last-{args.command}.log").open("w", encoding="utf-8") as log:
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                if line.startswith("Traceback") or "torch.OutOfMemoryError" in line or "Error executing job" in line:
                    failed = True
        status = process.wait()
    except KeyboardInterrupt:
        if process.poll() is None:
            process.terminate()
            process.wait()
        return 130
    return status or (1 if failed else 0)


if __name__ == "__main__":
    raise SystemExit(main())
