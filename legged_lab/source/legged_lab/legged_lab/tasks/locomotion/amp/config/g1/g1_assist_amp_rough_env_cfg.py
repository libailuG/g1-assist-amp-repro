import os
from isaaclab.utils.configclass import configclass
from legged_lab import LEGGED_LAB_ROOT_DIR
from .g1_amp_rough_env_cfg import G1AmpRoughEnvCfg, G1AmpRoughEnvCfg_PLAY

ASSIST_USD = os.path.join(LEGGED_LAB_ROOT_DIR, "data", "Robots", "Unitree", "g1_29dof_assist", "usd", "g1_29dof_assist_v1", "g1_29dof_assist.usd")

def configure_assist(cfg):
    # Preserve the supplied model masses, inertias and collision geometry.
    cfg.scene.robot.spawn.usd_path = ASSIST_USD
    # 1 ms physics/implicit PD integration; retain 20 ms policy updates.
    cfg.sim.dt = 0.001
    cfg.decimation = 20
    cfg.sim.render_interval = cfg.decimation
    if cfg.scene.contact_forces is not None:
        cfg.scene.contact_forces.update_period = cfg.sim.dt
    if cfg.scene.height_scanner is not None:
        cfg.scene.height_scanner.update_period = cfg.decimation * cfg.sim.dt
    # User supplied P/I/D table: apply P and D only, no integral controller.
    cfg.scene.robot.actuators = {name: actuator.copy() for name, actuator in cfg.scene.robot.actuators.items()}
    acts = cfg.scene.robot.actuators
    acts["N7520-14.3"].stiffness = {".*_hip_.*": 180.0, "waist_yaw_joint": 360.0}
    acts["N7520-14.3"].damping = {".*_hip_.*": 3.0, "waist_yaw_joint": 7.5}
    acts["N7520-22.5"].stiffness = {".*_hip_roll_.*": 180.0, ".*_knee_.*": 270.0}
    acts["N7520-22.5"].damping = {".*_hip_roll_.*": 3.0, ".*_knee_.*": 6.0}
    acts["N5020-16"].stiffness = {
        ".*_shoulder_.*": 56.0, ".*_elbow_.*": 56.0, ".*_wrist_roll.*": 56.0,
        ".*_ankle_.*": 72.0, "waist_.*_joint": 72.0,
    }
    acts["N5020-16"].damping = {
        ".*_shoulder_.*": 1.3, ".*_elbow_.*": 1.3, ".*_wrist_roll.*": 1.3,
        ".*_ankle_.*": 3.0, "waist_.*_joint": 7.5,
    }
    acts["W4010-25"].stiffness = 56.0
    acts["W4010-25"].damping = 1.3
    cfg.scene.height_scanner.debug_vis = False
    cfg.commands.base_velocity.debug_vis = False

@configclass
class G1AssistAmpRoughEnvCfg(G1AmpRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        configure_assist(self)

@configclass
class G1AssistAmpRoughEnvCfg_PLAY(G1AmpRoughEnvCfg_PLAY):
    def __post_init__(self):
        super().__post_init__()
        configure_assist(self)
