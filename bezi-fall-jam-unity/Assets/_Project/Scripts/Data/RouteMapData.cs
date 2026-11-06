using System.Collections.Generic;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>The handcrafted route graph (GDD §3 / §8).</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Route Map", fileName = "RouteMap_")]
    public class RouteMapData : ScriptableObject
    {
        public RestStopData startStop;
        public RestStopData destinationStop;
        public List<RestStopData> allStops = new List<RestStopData>();

        /// <summary>Number of legs in a run (the destination's row index).</summary>
        public int TotalLegs => destinationStop != null ? destinationStop.row : 0;

        /// <summary>Highest row index among all stops.</summary>
        public int MaxRow
        {
            get
            {
                int maxRow = 0;
                foreach (RestStopData stop in allStops)
                {
                    if (stop != null && stop.row > maxRow)
                    {
                        maxRow = stop.row;
                    }
                }
                return maxRow;
            }
        }

        /// <summary>Longest leg distance on the map, used to scale leg-length bars.</summary>
        public float MaxLegDistance
        {
            get
            {
                float maxDistance = 0f;
                foreach (RestStopData stop in allStops)
                {
                    if (stop != null && stop.leg.distanceMeters > maxDistance)
                    {
                        maxDistance = stop.leg.distanceMeters;
                    }
                }
                return maxDistance;
            }
        }

        /// <summary>Returns all stops in a row, in allStops order (left to right on the chart).</summary>
        public List<RestStopData> GetStopsInRow(int row)
        {
            var stops = new List<RestStopData>();
            foreach (RestStopData stop in allStops)
            {
                if (stop != null && stop.row == row)
                {
                    stops.Add(stop);
                }
            }
            return stops;
        }
    }
}
