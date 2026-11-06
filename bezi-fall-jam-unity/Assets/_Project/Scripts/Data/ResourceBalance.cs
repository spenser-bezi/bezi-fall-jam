using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Food/Water meters and drain multipliers. Start values from GDD §4 and §5.6.</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Balance/Resource Balance", fileName = "ResourceBalance")]
    public class ResourceBalance : ScriptableObject
    {
        [Header("Meters (GDD §4)")]
        public float maxMeter = 100f;
        public float startingFood = 100f;
        public float startingWater = 100f;

        [Header("Base drain per second (GDD §5.6)")]
        public float baseFoodDrain = 0.45f;
        public float baseWaterDrain = 0.45f;

        [Header("Multipliers (GDD §5.6)")]
        public float headwindFoodMultiplier = 1.25f;
        public float headwindWaterMultiplier = 1f;
        public float tailwindFoodMultiplier = 0.85f;
        public float tailwindWaterMultiplier = 0.85f;
        public float highBandFoodMultiplier = 1f;
        public float highBandWaterMultiplier = 1.3f;
        public float tightenFoodMultiplier = 1.5f;
        public float tightenWaterMultiplier = 1f;
        public float stormFoodMultiplier = 2f;
        public float stormWaterMultiplier = 2f;

        [Header("Starvation (GDD §4)")]
        [Tooltip("While either meter is empty, the rearmost goose leaves every this many seconds.")]
        public float starvationLossInterval = 3f;
    }
}
