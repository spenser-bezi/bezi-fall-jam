using System.Collections.Generic;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>
    /// Places snacks, ponds, and thermals along the leg by snack density (x trait snack multiplier), and spreads
    /// the leg's lost geese evenly between the start and end clear zones.
    /// </summary>
    public class PickupSpawner : DistanceSpawnerBase
    {
        [SerializeField] private List<PickupDefinition> definitions = new List<PickupDefinition>();

        private readonly List<PickupDefinition> regularPickups = new List<PickupDefinition>();
        private readonly Queue<float> lostGooseDistances = new Queue<float>();
        private PickupDefinition lostGooseDefinition;

        /// <inheritdoc />
        protected override void OnBeginLeg()
        {
            regularPickups.Clear();
            lostGooseDefinition = null;
            foreach (PickupDefinition definition in definitions)
            {
                if (definition == null || definition.prefab == null)
                {
                    continue;
                }
                if (definition.type == PickupType.LostGoose)
                {
                    lostGooseDefinition = definition;
                }
                else
                {
                    regularPickups.Add(definition);
                }
            }

            lostGooseDistances.Clear();
            int lostGeese = Leg.lostGeeseCount;
            float usableStart = LegStartZ + settings.legStartClearDistance;
            float usableLength = Mathf.Max(0f, LegEndZ - settings.legEndClearDistance - usableStart);
            for (int i = 0; i < lostGeese; i++)
            {
                float fraction = (i + 1f) / (lostGeese + 1f);
                lostGooseDistances.Enqueue(usableStart + usableLength * fraction);
            }
        }

        /// <inheritdoc />
        protected override float SpawnAt(float z)
        {
            float snackMultiplier = Mathf.Max(Mathf.Epsilon, Leg.SnackMultiplier);
            float spacing = Jitter(settings.GetSnackSpacing(Leg.snackDensity) / snackMultiplier);

            int index = WeightedRandom.PickIndex(regularPickups, d => d.weight, RandomValue());
            if (index >= 0)
            {
                SpawnPickup(regularPickups[index], z);
            }

            while (lostGooseDefinition != null && lostGooseDistances.Count > 0 && lostGooseDistances.Peek() <= z + spacing)
            {
                SpawnPickup(lostGooseDefinition, lostGooseDistances.Dequeue());
            }
            return spacing;
        }

        private void SpawnPickup(PickupDefinition definition, float z)
        {
            float x = RandomRange(-settings.spawnHalfWidth, settings.spawnHalfWidth);
            Vector3 position = new Vector3(x, GetSpawnHeight(definition.band, definition.groundAnchored), z);
            GameObject instance = SpawnTracked(definition.prefab, position);
            Pickup pickup = instance.GetComponent<Pickup>();
            if (pickup != null)
            {
                pickup.Initialize(definition);
            }
        }
    }
}
