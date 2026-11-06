using System.Collections.Generic;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>
    /// Streams hex tile rows ahead of the leader and recycles rows behind it (pooled). Biomes are picked
    /// with Perlin noise mapped onto the leg's biome weights so they form natural patches. The last rows of
    /// the leg use the destination biome so the lake appears on the horizon. Also starts the spawners.
    /// </summary>
    public class LegWorldGenerator : MonoBehaviour
    {
        private const float NoiseOffsetRange = 10000f;
        private const int ColumnCenterDivisor = 2;

        [SerializeField] private WorldGenSettings settings;
        [SerializeField] private ObstacleSpawner obstacleSpawner;
        [SerializeField] private PickupSpawner pickupSpawner;

        private readonly Dictionary<int, List<PooledTile>> activeRows = new Dictionary<int, List<PooledTile>>();
        private readonly Dictionary<GameObject, Stack<GameObject>> pool = new Dictionary<GameObject, Stack<GameObject>>();
        private readonly List<int> rowsToRecycle = new List<int>();
        private LegSettings leg;
        private Transform target;
        private HexGrid grid;
        private System.Random random;
        private Vector2 noiseOffset;
        private Vector3 origin;
        private int destinationStartRow;
        private bool isRunning;

        private struct PooledTile
        {
            public GameObject prefab;
            public GameObject instance;
        }

        public WorldGenSettings Settings => settings;

        /// <summary>Starts streaming a leg around the target (the leader). Called by FlightSceneController.</summary>
        public void BeginLeg(LegSettings legSettings, Transform followTarget)
        {
            leg = legSettings;
            target = followTarget;
            grid = new HexGrid(settings.hexRadius);
            int seed = System.Environment.TickCount;
            random = new System.Random(seed);
            noiseOffset = new Vector2(RandomRange(0f, NoiseOffsetRange), RandomRange(0f, NoiseOffsetRange));
            origin = new Vector3(0f, 0f, followTarget.position.z);
            int legRows = Mathf.CeilToInt(leg.distanceMeters / grid.RowSpacing);
            destinationStartRow = legRows - settings.destinationRows;

            RecycleAllRows();
            isRunning = true;
            UpdateRows();

            if (leg.HasFog)
            {
                RenderSettings.fogDensity *= settings.fogDensityMultiplier;
            }

            obstacleSpawner?.BeginLeg(leg, followTarget, random.Next());
            pickupSpawner?.BeginLeg(leg, followTarget, random.Next());
        }

        private void Update()
        {
            if (isRunning && target != null)
            {
                UpdateRows();
            }
        }

        private void UpdateRows()
        {
            int currentRow = grid.WorldZToRow(target.position.z - origin.z);
            int firstRow = currentRow - settings.rowsBehind;
            int lastRow = currentRow + settings.rowsAhead;

            rowsToRecycle.Clear();
            foreach (int row in activeRows.Keys)
            {
                if (row < firstRow || row > lastRow)
                {
                    rowsToRecycle.Add(row);
                }
            }
            foreach (int row in rowsToRecycle)
            {
                RecycleRow(row);
            }

            for (int row = firstRow; row <= lastRow; row++)
            {
                if (!activeRows.ContainsKey(row))
                {
                    BuildRow(row);
                }
            }
        }

        private void BuildRow(int row)
        {
            var tiles = new List<PooledTile>(settings.columns);
            int halfColumns = settings.columns / ColumnCenterDivisor;
            for (int columnIndex = 0; columnIndex < settings.columns; columnIndex++)
            {
                int column = columnIndex - halfColumns;
                BiomeData biome = PickBiome(column, row);
                GameObject prefab = biome != null ? biome.PickTile(RandomValue()) : null;
                if (prefab == null)
                {
                    continue;
                }
                GameObject instance = GetFromPool(prefab);
                instance.transform.SetPositionAndRotation(origin + grid.OffsetToWorld(column, row), Quaternion.identity);
                tiles.Add(new PooledTile { prefab = prefab, instance = instance });
            }
            activeRows[row] = tiles;
        }

        private BiomeData PickBiome(int column, int row)
        {
            if (row >= destinationStartRow && settings.destinationBiome != null)
            {
                return settings.destinationBiome;
            }
            if (leg.biomes.Count == 0)
            {
                return settings.destinationBiome;
            }
            float noise = Mathf.Clamp01(Mathf.PerlinNoise(
                (column + noiseOffset.x) * settings.biomeNoiseScale,
                (row + noiseOffset.y) * settings.biomeNoiseScale));
            int index = WeightedRandom.PickIndex(leg.biomes, entry => entry.biome != null ? entry.weight : 0f, noise);
            return index >= 0 ? leg.biomes[index].biome : settings.destinationBiome;
        }

        private GameObject GetFromPool(GameObject prefab)
        {
            if (pool.TryGetValue(prefab, out Stack<GameObject> stack) && stack.Count > 0)
            {
                GameObject pooled = stack.Pop();
                pooled.SetActive(true);
                return pooled;
            }
            return Instantiate(prefab, transform);
        }

        private void RecycleRow(int row)
        {
            if (!activeRows.TryGetValue(row, out List<PooledTile> tiles))
            {
                return;
            }
            foreach (PooledTile tile in tiles)
            {
                if (tile.instance == null)
                {
                    continue;
                }
                tile.instance.SetActive(false);
                if (!pool.TryGetValue(tile.prefab, out Stack<GameObject> stack))
                {
                    stack = new Stack<GameObject>();
                    pool[tile.prefab] = stack;
                }
                stack.Push(tile.instance);
            }
            activeRows.Remove(row);
        }

        private void RecycleAllRows()
        {
            rowsToRecycle.Clear();
            rowsToRecycle.AddRange(activeRows.Keys);
            foreach (int row in rowsToRecycle)
            {
                RecycleRow(row);
            }
        }

        private float RandomRange(float min, float max) => min + (float)random.NextDouble() * (max - min);

        private float RandomValue() => (float)random.NextDouble();
    }
}
