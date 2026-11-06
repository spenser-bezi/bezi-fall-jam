using System.Collections.Generic;
using FallIsLife.Core;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>
    /// Shared logic for spawners that place items along the leg's distance: spawns ahead of the target,
    /// despawns behind it, and keeps clear zones at the start and end of the leg.
    /// </summary>
    public abstract class DistanceSpawnerBase : MonoBehaviour
    {
        [SerializeField] protected WorldGenSettings settings;
        [SerializeField] protected FlightBalance flightBalance;

        private readonly List<GameObject> spawned = new List<GameObject>();
        private float nextSpawnZ;
        private bool isRunning;

        protected LegSettings Leg { get; private set; }
        protected Transform Target { get; private set; }
        protected System.Random Random { get; private set; }
        protected float LegStartZ { get; private set; }
        protected float LegEndZ { get; private set; }

        /// <summary>Starts spawning for a leg. Called by LegWorldGenerator.</summary>
        public void BeginLeg(LegSettings leg, Transform target, int seed)
        {
            ClearSpawned();
            Leg = leg;
            Target = target;
            Random = new System.Random(seed);
            LegStartZ = target.position.z;
            LegEndZ = LegStartZ + leg.distanceMeters;
            nextSpawnZ = LegStartZ + settings.legStartClearDistance;
            isRunning = true;
            OnBeginLeg();
        }

        /// <summary>Destroys everything this spawner created.</summary>
        public void ClearSpawned()
        {
            foreach (GameObject item in spawned)
            {
                if (item != null)
                {
                    Destroy(item);
                }
            }
            spawned.Clear();
        }

        /// <summary>Hook for subclasses to prepare per-leg data.</summary>
        protected virtual void OnBeginLeg()
        {
        }

        /// <summary>Spawns everything at one distance (Z). Return the spacing to the next spawn.</summary>
        protected abstract float SpawnAt(float z);

        /// <summary>Instantiates a prefab under this spawner and tracks it for despawning.</summary>
        protected GameObject SpawnTracked(GameObject prefab, Vector3 position)
        {
            GameObject instance = Instantiate(prefab, position, Quaternion.identity, transform);
            spawned.Add(instance);
            return instance;
        }

        /// <summary>Returns a uniform random float in [min, max).</summary>
        protected float RandomRange(float min, float max) => min + (float)Random.NextDouble() * (max - min);

        /// <summary>Returns a uniform random float in [0, 1).</summary>
        protected float RandomValue() => (float)Random.NextDouble();

        /// <summary>Applies the settings' jitter to a base spacing.</summary>
        protected float Jitter(float spacing) => spacing * RandomRange(1f - settings.spacingJitter, 1f + settings.spacingJitter);

        /// <summary>Returns a spawn height for a band, or ground height when anchored.</summary>
        protected float GetSpawnHeight(AltitudeBand band, bool groundAnchored)
        {
            if (groundAnchored)
            {
                return 0f;
            }
            Vector2 range = flightBalance.GetBandRange(band);
            return RandomRange(range.x, range.y);
        }

        protected virtual void Update()
        {
            if (!isRunning || Target == null)
            {
                return;
            }

            float spawnLimitZ = Mathf.Min(Target.position.z + settings.spawnAheadDistance, LegEndZ - settings.legEndClearDistance);
            while (nextSpawnZ < spawnLimitZ)
            {
                float spacing = SpawnAt(nextSpawnZ);
                nextSpawnZ += Mathf.Max(spacing, settings.hexRadius);
            }

            float despawnZ = Target.position.z - settings.despawnBehindDistance;
            for (int i = spawned.Count - 1; i >= 0; i--)
            {
                GameObject item = spawned[i];
                if (item == null)
                {
                    spawned.RemoveAt(i);
                }
                else if (item.transform.position.z < despawnZ)
                {
                    Destroy(item);
                    spawned.RemoveAt(i);
                }
            }
        }
    }
}
