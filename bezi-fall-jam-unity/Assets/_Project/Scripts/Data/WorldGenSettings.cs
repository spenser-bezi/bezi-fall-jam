using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Hex world streaming and spawn spacing.</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Balance/World Gen Settings", fileName = "WorldGenSettings")]
    public class WorldGenSettings : ScriptableObject
    {
        [Header("Hex grid (Foundation plan 3.5 / section 7)")]
        public float hexRadius = 10f;
        public int columns = 11;
        public int rowsAhead = 30;
        public int rowsBehind = 4;
        public float biomeNoiseScale = 0.12f;

        [Header("Destination")]
        [Tooltip("Biome forced for the last rows of the leg so the destination lake appears on the horizon.")]
        public BiomeData destinationBiome;
        public int destinationRows = 5;

        [Header("Spawning")]
        public float spawnAheadDistance = 320f;
        public float despawnBehindDistance = 40f;
        [Tooltip("Half-width of the corridor where obstacles and pickups are placed.")]
        public float spawnHalfWidth = 60f;
        public float legStartClearDistance = 90f;
        public float legEndClearDistance = 140f;
        [Tooltip("Meters between obstacle rows for hazard level 1, 2, 3.")]
        public float[] obstacleSpacingByHazard = { 70f, 50f, 36f };
        [Tooltip("Meters between snack spawns for snack density 1, 2, 3.")]
        public float[] snackSpacingByDensity = { 80f, 55f, 38f };
        [Range(0f, 1f)] public float spacingJitter = 0.35f;
        [Tooltip("Minimum lateral distance between obstacles placed in the same row.")]
        public float minObstacleLateralGap = 22f;

        [Header("Fog")]
        public float fogDensityMultiplier = 2.5f;

        /// <summary>Returns obstacle row spacing for a 1-3 hazard level.</summary>
        public float GetObstacleSpacing(int hazardLevel) => GetByRating(obstacleSpacingByHazard, hazardLevel);

        /// <summary>Returns snack spacing for a 1-3 snack density.</summary>
        public float GetSnackSpacing(int snackDensity) => GetByRating(snackSpacingByDensity, snackDensity);

        private static float GetByRating(float[] values, int rating)
        {
            int index = Mathf.Clamp(rating - LegSettings.MinRating, 0, values.Length - 1);
            return values[index];
        }
    }
}
