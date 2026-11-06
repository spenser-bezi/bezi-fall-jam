using System.Collections.Generic;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>A hex tile biome (GDD §8) and the tile logic prefabs it can spawn.</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Biome", fileName = "Biome_")]
    public class BiomeData : ScriptableObject
    {
        public string id;
        public List<WeightedPrefab> tiles = new List<WeightedPrefab>();

        /// <summary>Picks a tile prefab with a normalized roll in [0,1). Returns null if no tiles are set.</summary>
        public GameObject PickTile(float normalizedRoll)
        {
            int index = WeightedRandom.PickIndex(tiles, entry => entry.prefab != null ? entry.weight : 0f, normalizedRoll);
            return index >= 0 ? tiles[index].prefab : null;
        }
    }
}
