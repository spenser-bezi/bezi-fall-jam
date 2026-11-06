using System;
using System.Collections.Generic;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>
    /// Properties of the flight leg TO a rest stop (GDD §3: a leg belongs to its destination node).
    /// </summary>
    [Serializable]
    public class LegSettings
    {
        public const int MinRating = 1;
        public const int MaxRating = 3;

        [Min(0f)] public float distanceMeters = 1500f;
        [Tooltip("Signed m/s along the forward axis. Positive = tailwind, negative = headwind.")]
        public float windSpeed;
        public WeatherType weather = WeatherType.Clear;
        [Range(MinRating, MaxRating)] public int hazardLevel = MinRating;
        [Range(MinRating, MaxRating)] public int snackDensity = MinRating;
        [Min(0)] public int lostGeeseCount = 1;
        public List<BiomeWeight> biomes = new List<BiomeWeight>();
        public List<RouteTraitData> traits = new List<RouteTraitData>();

        /// <summary>Hazard level after trait deltas (e.g. Calm Skies), clamped to 1-3.</summary>
        public int EffectiveHazardLevel
        {
            get
            {
                int level = hazardLevel;
                foreach (RouteTraitData trait in traits)
                {
                    if (trait != null)
                    {
                        level += trait.hazardDelta;
                    }
                }
                return Mathf.Clamp(level, MinRating, MaxRating);
            }
        }

        /// <summary>Product of all trait snack multipliers.</summary>
        public float SnackMultiplier
        {
            get
            {
                float multiplier = 1f;
                foreach (RouteTraitData trait in traits)
                {
                    if (trait != null)
                    {
                        multiplier *= trait.snackMultiplier;
                    }
                }
                return multiplier;
            }
        }

        /// <summary>Sum of all trait jet-stream bonuses (m/s, applied in the High band).</summary>
        public float JetStreamBonus
        {
            get
            {
                float bonus = 0f;
                foreach (RouteTraitData trait in traits)
                {
                    if (trait != null)
                    {
                        bonus += trait.jetStreamBonus;
                    }
                }
                return bonus;
            }
        }

        /// <summary>True when the weather or any trait asks for fog.</summary>
        public bool HasFog
        {
            get
            {
                if (weather == WeatherType.Foggy)
                {
                    return true;
                }
                foreach (RouteTraitData trait in traits)
                {
                    if (trait != null && trait.enableFog)
                    {
                        return true;
                    }
                }
                return false;
            }
        }

        /// <summary>Product of all trait multipliers for an obstacle category.</summary>
        public float GetObstacleMultiplier(ObstacleCategory category)
        {
            float multiplier = 1f;
            foreach (RouteTraitData trait in traits)
            {
                if (trait != null)
                {
                    multiplier *= trait.GetObstacleMultiplier(category);
                }
            }
            return multiplier;
        }
    }
}
