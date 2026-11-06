using System;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>A biome and its relative weight for a leg.</summary>
    [Serializable]
    public class BiomeWeight
    {
        public BiomeData biome;
        [Min(0f)] public float weight = 1f;
    }

    /// <summary>A prefab and its relative pick weight.</summary>
    [Serializable]
    public class WeightedPrefab
    {
        public GameObject prefab;
        [Min(0f)] public float weight = 1f;
    }

    /// <summary>Spawn-weight multiplier for one obstacle category.</summary>
    [Serializable]
    public class ObstacleMultiplier
    {
        public ObstacleCategory category;
        [Min(0f)] public float multiplier = 1f;
    }
}
