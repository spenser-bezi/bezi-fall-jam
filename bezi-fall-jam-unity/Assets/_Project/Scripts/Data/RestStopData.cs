using System.Collections.Generic;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>One lake on the route map (GDD §8). Its LegSettings describe the flight that arrives here.</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Rest Stop", fileName = "RestStop_")]
    public class RestStopData : ScriptableObject
    {
        public string displayName;
        public string subtitle;
        [Tooltip("0 = start, increasing southward. The destination's row equals the number of legs.")]
        [Min(0)] public int row;
        public Sprite postcard;
        [Tooltip("Goose-meals of food the lake provides overnight (GDD §6).")]
        [Min(0)] public int foodCapacity;
        [Tooltip("Goose-meals of water the lake provides overnight (GDD §6).")]
        [Min(0)] public int waterCapacity;
        [Min(0)] public int recruitsOnArrival;
        public List<RestStopData> nextStops = new List<RestStopData>();
        public LegSettings leg = new LegSettings();
    }
}
