using FallIsLife.Core;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Spawn rules for one obstacle type (GDD §5.8).</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Obstacle Definition", fileName = "Obstacle_")]
    public class ObstacleDefinition : ScriptableObject
    {
        public GameObject prefab;
        public ObstacleCategory category;
        public AltitudeBand band = AltitudeBand.Low;
        [Min(0f)] public float weight = 1f;
        [Range(LegSettings.MinRating, LegSettings.MaxRating)] public int minHazardLevel = LegSettings.MinRating;
        public bool warnsOnHud;
        [Tooltip("Placed on the ground (Y = 0) instead of floating inside its band.")]
        public bool groundAnchored = true;
    }
}
