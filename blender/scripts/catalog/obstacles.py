"""Obstacle and snack pickup assets (P2, Art Workflow 5.3). Seeds 4000-4999."""
from registry import OBSTACLE_TRIANGLE_BUDGET, PROP_TRIANGLE_BUDGET, AssetSpec

OBSTACLE_CATEGORY = "Environment/Obstacles"
PROP_CATEGORY = "Environment/Props"
OBSTACLE_KIND = "obstacle"
PROP_KIND = "prop"
GROUND_MODULE = "obstacles.ground"
WINDMILL_MODULE = "obstacles.windmill"
SKY_MODULE = "obstacles.sky"
PLANE_MODULE = "obstacles.plane"
SNACK_MODULE = "obstacles.snacks"


def _obstacle(asset_id, mesh_name, module, seed, animated=False):
    return AssetSpec(asset_id, mesh_name, module, OBSTACLE_CATEGORY, OBSTACLE_KIND, OBSTACLE_TRIANGLE_BUDGET, seed,
                     animated=animated)


def _snack(asset_id, mesh_name, seed):
    return AssetSpec(asset_id, mesh_name, SNACK_MODULE, PROP_CATEGORY, PROP_KIND, PROP_TRIANGLE_BUDGET, seed)


ASSETS = [
    _obstacle("obstacle.tree_cluster_a", "SM_TreeCluster_A", GROUND_MODULE, 4001),
    _obstacle("obstacle.tree_cluster_b", "SM_TreeCluster_B", GROUND_MODULE, 4002),
    _obstacle("obstacle.steeple", "SM_Steeple", GROUND_MODULE, 4010),
    _obstacle("obstacle.clock_tower", "SM_ClockTower", GROUND_MODULE, 4011),
    _obstacle("obstacle.silo_tall", "SM_SiloTall", GROUND_MODULE, 4012),
    _obstacle("obstacle.windmill_base", "SM_Windmill_Base", WINDMILL_MODULE, 4020),
    _obstacle("obstacle.windmill_blades", "SM_Windmill_Blades", WINDMILL_MODULE, 4021, animated=True),
    _obstacle("obstacle.power_tower", "SM_PowerTower", GROUND_MODULE, 4030),
    _obstacle("obstacle.power_wire", "SM_PowerWire", GROUND_MODULE, 4031),
    _obstacle("obstacle.balloon_a", "SM_Balloon_A", SKY_MODULE, 4040),
    _obstacle("obstacle.balloon_b", "SM_Balloon_B", SKY_MODULE, 4041),
    _obstacle("obstacle.balloon_c", "SM_Balloon_C", SKY_MODULE, 4042),
    _obstacle("obstacle.plane", "SM_Plane", PLANE_MODULE, 4050),
    _obstacle("obstacle.plane_prop", "SM_Plane_Prop", PLANE_MODULE, 4051, animated=True),
    _obstacle("obstacle.storm_cloud", "SM_StormCloud", SKY_MODULE, 4060),
    _obstacle("obstacle.lightning", "SM_Lightning", SKY_MODULE, 4061),
    _obstacle("obstacle.fog_puff", "SM_FogPuff", SKY_MODULE, 4070),
    _snack("prop.snack_corn", "SM_Snack_Corn", 4101),
    _snack("prop.snack_apple", "SM_Snack_Apple", 4102),
    _snack("prop.snack_pumpkin", "SM_Snack_Pumpkin", 4103),
]

GROUPS = {
    "obstacles": [spec.asset_id for spec in ASSETS if spec.kind == OBSTACLE_KIND],
    "snacks": [spec.asset_id for spec in ASSETS if spec.kind == PROP_KIND],
    "obstacles_animated": [spec.asset_id for spec in ASSETS if spec.animated],
}
