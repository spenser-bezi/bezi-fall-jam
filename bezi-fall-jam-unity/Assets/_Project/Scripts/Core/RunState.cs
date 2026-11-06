using System.Collections.Generic;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.Core
{
    /// <summary>Outcome of the whole run.</summary>
    public enum RunOutcome
    {
        InProgress,
        Won,
        Lost
    }

    /// <summary>
    /// Plain C# state for one migration run. Owned by GameFlowManager and read by every phase scene.
    /// </summary>
    public class RunState
    {
        /// <summary>1-based day of the leg that is planned or being flown next.</summary>
        public int DayIndex { get; set; } = 1;
        public RestStopData CurrentStop { get; set; }
        public RestStopData NextStop { get; set; }
        public int FlockSize { get; set; }
        public int StartingFlockSize { get; set; }
        public float Food { get; set; }
        public float Water { get; set; }
        public int TotalLegs { get; set; }
        public int TotalRecruits { get; set; }
        public int SnacksEaten { get; set; }
        public RunOutcome Outcome { get; set; } = RunOutcome.InProgress;
        public bool IsDebugRun { get; set; }
        public NightReport LastNight { get; set; }
        public List<LegResult> History { get; } = new List<LegResult>();
        public List<RestStopData> VisitedStops { get; } = new List<RestStopData>();
        public Dictionary<GooseLossReason, int> GeeseLostByReason { get; } = new Dictionary<GooseLossReason, int>();

        /// <summary>Creates a fresh run at the route's start stop using balance start values.</summary>
        public static RunState CreateNew(RouteMapData routeMap, FlockBalance flockBalance, ResourceBalance resourceBalance)
        {
            var state = new RunState
            {
                CurrentStop = routeMap != null ? routeMap.startStop : null,
                FlockSize = flockBalance.startingFlockSize,
                StartingFlockSize = flockBalance.startingFlockSize,
                Food = resourceBalance.startingFood,
                Water = resourceBalance.startingWater,
                TotalLegs = routeMap != null ? routeMap.TotalLegs : 0
            };
            if (state.CurrentStop != null)
            {
                state.VisitedStops.Add(state.CurrentStop);
            }
            foreach (GooseLossReason reason in System.Enum.GetValues(typeof(GooseLossReason)))
            {
                state.GeeseLostByReason[reason] = 0;
            }
            return state;
        }

        /// <summary>Total geese that ever belonged to the flock this run (start + recruits).</summary>
        public int TotalGeeseThisRun => StartingFlockSize + TotalRecruits;

        /// <summary>Returns how many geese were lost for a reason across the run.</summary>
        public int GetLost(GooseLossReason reason)
        {
            return GeeseLostByReason.TryGetValue(reason, out int count) ? count : 0;
        }

        /// <summary>Folds a completed leg into the run totals.</summary>
        public void ApplyLegResult(LegResult result)
        {
            History.Add(result);
            FlockSize = result.geeseAtEnd;
            Food = result.foodAtEnd;
            Water = result.waterAtEnd;
            TotalRecruits += result.recruits;
            SnacksEaten += result.snacksEaten;
            foreach (GooseLossReason reason in System.Enum.GetValues(typeof(GooseLossReason)))
            {
                GeeseLostByReason[reason] = GetLost(reason) + result.GetLost(reason);
            }
        }

        /// <summary>
        /// Applies the GDD §6 feeding rule plus overnight recruits at the current stop and returns the report.
        /// refillFraction = min(1, capacity / flockSize); meter += (max - meter) * refillFraction.
        /// </summary>
        public NightReport ApplyNightRest(RestStopData stop, LegResult lastLeg, ResourceBalance resourceBalance, FlockBalance flockBalance)
        {
            var report = new NightReport
            {
                dayCompleted = DayIndex,
                lakeName = stop != null ? stop.displayName : string.Empty,
                geeseStartedLeg = lastLeg.geeseAtStart,
                geeseArrived = FlockSize,
                foodBefore = Food,
                waterBefore = Water
            };

            if (stop != null && FlockSize > 0)
            {
                float foodRefill = Mathf.Min(1f, (float)stop.foodCapacity / FlockSize);
                float waterRefill = Mathf.Min(1f, (float)stop.waterCapacity / FlockSize);
                Food += (resourceBalance.maxMeter - Food) * foodRefill;
                Water += (resourceBalance.maxMeter - Water) * waterRefill;

                int recruits = stop.recruitsOnArrival;
                foreach (RouteTraitData trait in stop.leg.traits)
                {
                    if (trait == null || trait.recruitsBonus <= 0)
                    {
                        continue;
                    }
                    recruits += trait.recruitsBonus;
                    report.traitMessages.Add($"{trait.displayName}: {trait.recruitsBonus} geese joined you!");
                }

                int roomInFlock = flockBalance.maxFlockSize - FlockSize;
                int acceptedRecruits = Mathf.Clamp(recruits, 0, roomInFlock);
                FlockSize += acceptedRecruits;
                TotalRecruits += acceptedRecruits;
                report.geeseRecruited = acceptedRecruits;
            }

            report.foodAfter = Food;
            report.waterAfter = Water;
            LastNight = report;
            return report;
        }

        /// <summary>Star rating per GDD §9: arrive, arrive with the two-star minimum, arrive with the starting flock size.</summary>
        public int CalculateStars(FlockBalance flockBalance)
        {
            if (Outcome != RunOutcome.Won || FlockSize <= 0)
            {
                return 0;
            }
            if (FlockSize >= StartingFlockSize)
            {
                return flockBalance.maxStars;
            }
            if (FlockSize >= flockBalance.twoStarMinGeese)
            {
                return flockBalance.maxStars - 1;
            }
            return 1;
        }
    }
}
