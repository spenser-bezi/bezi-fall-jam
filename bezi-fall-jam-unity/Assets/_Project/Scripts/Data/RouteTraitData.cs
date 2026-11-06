using System.Collections.Generic;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Named leg condition in the Pacific Drive style (GDD §7).</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Route Trait", fileName = "Trait_")]
    public class RouteTraitData : ScriptableObject
    {
        public string displayName;
        [TextArea] public string description;
        public Sprite icon;
        public List<ObstacleMultiplier> obstacleMultipliers = new List<ObstacleMultiplier>();
        [Min(0f)] public float snackMultiplier = 1f;
        [Tooltip("Extra tailwind (m/s) while in the High band.")]
        [Min(0f)] public float jetStreamBonus;
        public bool enableFog;
        [Tooltip("Added to the leg's hazard pips (e.g. -1 for Calm Skies).")]
        public int hazardDelta;
        [Tooltip("Geese that join overnight at this lake.")]
        [Min(0)] public int recruitsBonus;

        /// <summary>Returns this trait's multiplier for an obstacle category (1 when unlisted).</summary>
        public float GetObstacleMultiplier(ObstacleCategory category)
        {
            foreach (ObstacleMultiplier entry in obstacleMultipliers)
            {
                if (entry.category == category)
                {
                    return entry.multiplier;
                }
            }
            return 1f;
        }
    }
}
