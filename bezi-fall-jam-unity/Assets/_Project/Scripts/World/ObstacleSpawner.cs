using System.Collections.Generic;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>
    /// Places obstacle rows along the leg. Row spacing and max obstacles per row follow the effective hazard
    /// level; picks are weighted by definition weight x trait multipliers. Traits that boost a category
    /// (e.g. Regional Airport) let it spawn even below its minimum hazard level.
    /// </summary>
    public class ObstacleSpawner : DistanceSpawnerBase
    {
        private const int MaxPlacementAttempts = 6;

        [SerializeField] private List<ObstacleDefinition> definitions = new List<ObstacleDefinition>();

        private readonly List<ObstacleDefinition> eligible = new List<ObstacleDefinition>();
        private readonly List<float> rowPositions = new List<float>();
        private int hazardLevel;

        /// <inheritdoc />
        protected override void OnBeginLeg()
        {
            hazardLevel = Leg.EffectiveHazardLevel;
            eligible.Clear();
            foreach (ObstacleDefinition definition in definitions)
            {
                if (definition == null || definition.prefab == null)
                {
                    continue;
                }
                bool boostedByTrait = Leg.GetObstacleMultiplier(definition.category) > 1f;
                if (definition.minHazardLevel <= hazardLevel || boostedByTrait)
                {
                    eligible.Add(definition);
                }
            }
        }

        /// <inheritdoc />
        protected override float SpawnAt(float z)
        {
            float spacing = Jitter(settings.GetObstacleSpacing(hazardLevel));
            if (eligible.Count == 0)
            {
                return spacing;
            }

            int count = Random.Next(LegSettings.MinRating, hazardLevel + 1);
            rowPositions.Clear();
            for (int i = 0; i < count; i++)
            {
                int index = WeightedRandom.PickIndex(eligible, d => d.weight * Leg.GetObstacleMultiplier(d.category), RandomValue());
                if (index < 0)
                {
                    break;
                }
                if (!TryPickLateralPosition(out float x))
                {
                    continue;
                }

                ObstacleDefinition definition = eligible[index];
                Vector3 position = new Vector3(x, GetSpawnHeight(definition.band, definition.groundAnchored), z);
                GameObject instance = SpawnTracked(definition.prefab, position);
                Obstacle obstacle = instance.GetComponent<Obstacle>();
                if (obstacle != null)
                {
                    obstacle.Initialize(definition, Target);
                }
            }
            return spacing;
        }

        private bool TryPickLateralPosition(out float x)
        {
            for (int attempt = 0; attempt < MaxPlacementAttempts; attempt++)
            {
                x = RandomRange(-settings.spawnHalfWidth, settings.spawnHalfWidth);
                bool overlaps = false;
                foreach (float existing in rowPositions)
                {
                    if (Mathf.Abs(existing - x) < settings.minObstacleLateralGap)
                    {
                        overlaps = true;
                        break;
                    }
                }
                if (!overlaps)
                {
                    rowPositions.Add(x);
                    return true;
                }
            }
            x = 0f;
            return false;
        }
    }
}
