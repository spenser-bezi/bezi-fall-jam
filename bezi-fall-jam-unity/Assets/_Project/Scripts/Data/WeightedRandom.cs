using System;
using System.Collections.Generic;

namespace FallIsLife.Data
{
    /// <summary>Helpers for weighted picks used by world generation and spawners.</summary>
    public static class WeightedRandom
    {
        /// <summary>
        /// Picks an index using a normalized roll in [0,1) against the given weights.
        /// Returns -1 when the list is empty or all weights are zero.
        /// </summary>
        public static int PickIndex<T>(IReadOnlyList<T> items, Func<T, float> getWeight, float normalizedRoll)
        {
            float total = 0f;
            for (int i = 0; i < items.Count; i++)
            {
                total += Math.Max(0f, getWeight(items[i]));
            }
            if (total <= 0f)
            {
                return -1;
            }

            float target = normalizedRoll * total;
            float cumulative = 0f;
            int lastValid = -1;
            for (int i = 0; i < items.Count; i++)
            {
                float weight = Math.Max(0f, getWeight(items[i]));
                if (weight <= 0f)
                {
                    continue;
                }
                lastValid = i;
                cumulative += weight;
                if (target < cumulative)
                {
                    return i;
                }
            }
            return lastValid;
        }
    }
}
