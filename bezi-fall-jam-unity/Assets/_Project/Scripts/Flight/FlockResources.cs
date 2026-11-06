using FallIsLife.Core;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Flock-wide Food/Water meters with GDD §5.6 drain multipliers and the GDD §4 starvation rule
    /// (while either meter is empty, the rearmost goose leaves every few seconds).
    /// </summary>
    public class FlockResources : MonoBehaviour
    {
        private ResourceBalance balance;
        private FlockController flock;
        private float legWind;
        private bool drainPaused;
        private float timedPauseRemaining;
        private int stormZoneCount;
        private float starvationTimer;
        private bool isRunning;

        public float Food { get; private set; }
        public float Water { get; private set; }
        public float MaxMeter => balance != null ? balance.maxMeter : 0f;
        public float FoodNormalized => MaxMeter > 0f ? Food / MaxMeter : 0f;
        public float WaterNormalized => MaxMeter > 0f ? Water / MaxMeter : 0f;
        public int SnacksEaten { get; private set; }
        public bool IsInStorm => stormZoneCount > 0;
        public bool IsDrainPaused => drainPaused || timedPauseRemaining > 0f;

        /// <summary>Starts draining from the given meter values. Called by FlightSceneController.</summary>
        public void Initialize(ResourceBalance resourceBalance, FlockController owner, float startFood, float startWater, float windSpeed)
        {
            balance = resourceBalance;
            flock = owner;
            legWind = windSpeed;
            Food = Mathf.Clamp(startFood, 0f, balance.maxMeter);
            Water = Mathf.Clamp(startWater, 0f, balance.maxMeter);
            isRunning = true;
            RaiseChanged();
        }

        /// <summary>Adds food (snack pickup). Counts as one snack eaten.</summary>
        public void AddFood(float amount)
        {
            Food = Mathf.Clamp(Food + amount, 0f, balance.maxMeter);
            SnacksEaten++;
            RaiseChanged();
        }

        /// <summary>Adds water (pond pickup).</summary>
        public void AddWater(float amount)
        {
            Water = Mathf.Clamp(Water + amount, 0f, balance.maxMeter);
            RaiseChanged();
        }

        /// <summary>Pauses or resumes drain indefinitely (e.g. landing, cutscenes).</summary>
        public void SetDrainPaused(bool isPaused)
        {
            drainPaused = isPaused;
        }

        /// <summary>Pauses drain for a duration (thermals). Overlapping calls keep the longest remaining time.</summary>
        public void PauseDrainFor(float seconds)
        {
            timedPauseRemaining = Mathf.Max(timedPauseRemaining, seconds);
        }

        /// <summary>Enters or exits a storm zone (drain multiplier). Supports overlapping zones.</summary>
        public void SetInStorm(bool isInside)
        {
            stormZoneCount = Mathf.Max(0, stormZoneCount + (isInside ? 1 : -1));
        }

        /// <summary>Stops all drain and starvation (leg over).</summary>
        public void StopDraining()
        {
            isRunning = false;
        }

        private void Update()
        {
            if (!isRunning || flock == null || flock.Leader == null)
            {
                return;
            }

            float deltaTime = Time.deltaTime;
            timedPauseRemaining = Mathf.Max(0f, timedPauseRemaining - deltaTime);

            if (!IsDrainPaused)
            {
                Food = Mathf.Max(0f, Food - balance.baseFoodDrain * CalculateFoodMultiplier() * deltaTime);
                Water = Mathf.Max(0f, Water - balance.baseWaterDrain * CalculateWaterMultiplier() * deltaTime);
                RaiseChanged();
            }

            UpdateStarvation(deltaTime);
        }

        private float CalculateFoodMultiplier()
        {
            float multiplier = 1f;
            if (legWind < 0f)
            {
                multiplier *= balance.headwindFoodMultiplier;
            }
            else if (legWind > 0f)
            {
                multiplier *= balance.tailwindFoodMultiplier;
            }
            if (flock.Leader.CurrentBand == AltitudeBand.High)
            {
                multiplier *= balance.highBandFoodMultiplier;
            }
            if (flock.Leader.IsTightening)
            {
                multiplier *= balance.tightenFoodMultiplier;
            }
            if (IsInStorm)
            {
                multiplier *= balance.stormFoodMultiplier;
            }
            return multiplier;
        }

        private float CalculateWaterMultiplier()
        {
            float multiplier = 1f;
            if (legWind < 0f)
            {
                multiplier *= balance.headwindWaterMultiplier;
            }
            else if (legWind > 0f)
            {
                multiplier *= balance.tailwindWaterMultiplier;
            }
            if (flock.Leader.CurrentBand == AltitudeBand.High)
            {
                multiplier *= balance.highBandWaterMultiplier;
            }
            if (flock.Leader.IsTightening)
            {
                multiplier *= balance.tightenWaterMultiplier;
            }
            if (IsInStorm)
            {
                multiplier *= balance.stormWaterMultiplier;
            }
            return multiplier;
        }

        private void UpdateStarvation(float deltaTime)
        {
            bool isStarving = Food <= 0f || Water <= 0f;
            if (!isStarving || flock.FlockSize <= 0)
            {
                starvationTimer = 0f;
                return;
            }

            starvationTimer += deltaTime;
            if (starvationTimer >= balance.starvationLossInterval)
            {
                starvationTimer = 0f;
                flock.LoseGoose(Food <= 0f ? GooseLossReason.Hunger : GooseLossReason.Thirst);
            }
        }

        private void RaiseChanged()
        {
            GameEvents.RaiseResourceChanged(ResourceType.Food, FoodNormalized);
            GameEvents.RaiseResourceChanged(ResourceType.Water, WaterNormalized);
        }
    }
}
