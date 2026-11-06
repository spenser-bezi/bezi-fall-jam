using FallIsLife.Core;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Tracks leg distance, progress, and ETA. When the distance is flown it runs the auto-landing,
    /// then reports the LegResult to GameFlowManager.CompleteLeg. Also ends the leg if the flock is lost.
    /// </summary>
    public class LegProgressTracker : MonoBehaviour
    {
        private const float MinSpeedForEta = 0.1f;

        private FlightBalance balance;
        private FlockController flock;
        private FlockResources resources;
        private string destinationName;
        private float startZ;
        private float landingTimer;
        private bool isTracking;
        private bool isCompleted;

        public float TotalDistance { get; private set; }
        public float DistanceFlown { get; private set; }
        public float Progress => TotalDistance > 0f ? Mathf.Clamp01(DistanceFlown / TotalDistance) : 0f;
        public float RemainingDistance => Mathf.Max(0f, TotalDistance - DistanceFlown);
        public bool IsLanding { get; private set; }
        public bool IsCompleted => isCompleted;

        /// <summary>Estimated seconds to arrival at the leader's current forward speed.</summary>
        public float EtaSeconds
        {
            get
            {
                float speed = flock != null && flock.Leader != null ? flock.Leader.ForwardSpeed : 0f;
                return RemainingDistance / Mathf.Max(MinSpeedForEta, speed > 0f ? speed : balance.baseForwardSpeed);
            }
        }

        /// <summary>Starts tracking a leg. Called by FlightSceneController after the flock spawns.</summary>
        public void Initialize(FlightBalance flightBalance, FlockController owner, FlockResources flockResources, float distanceMeters, string destination)
        {
            balance = flightBalance;
            flock = owner;
            resources = flockResources;
            destinationName = destination;
            TotalDistance = distanceMeters;
            startZ = flock.LeaderPosition.z;
            DistanceFlown = 0f;
            isTracking = true;
            isCompleted = false;
            flock.FlockEmptied += HandleFlockEmptied;
            GameEvents.RaiseLegProgressChanged(0f);
        }

        /// <summary>Debug helper: jumps straight to landing (used by tests and editor debug tools).</summary>
        public void DebugForceArrival()
        {
            if (!isCompleted && !IsLanding)
            {
                BeginLanding();
            }
        }

        private void OnDestroy()
        {
            if (flock != null)
            {
                flock.FlockEmptied -= HandleFlockEmptied;
            }
        }

        private void Update()
        {
            if (!isTracking || isCompleted || flock.Leader == null)
            {
                return;
            }

            DistanceFlown = flock.LeaderPosition.z - startZ;
            GameEvents.RaiseLegProgressChanged(Progress);

            if (!IsLanding && DistanceFlown >= TotalDistance)
            {
                BeginLanding();
            }

            if (IsLanding)
            {
                landingTimer -= Time.deltaTime;
                if (landingTimer <= 0f)
                {
                    Complete();
                }
            }
        }

        private void BeginLanding()
        {
            IsLanding = true;
            landingTimer = balance.landingDuration;
            flock.Leader.BeginLanding();
            resources.SetDrainPaused(true);
        }

        private void HandleFlockEmptied()
        {
            Complete();
        }

        private void Complete()
        {
            if (isCompleted)
            {
                return;
            }
            isCompleted = true;
            resources.StopDraining();

            var result = new LegResult
            {
                destinationName = destinationName,
                geeseAtStart = flock.StartingSize,
                geeseAtEnd = flock.FlockSize,
                recruits = flock.RecruitsThisLeg,
                foodAtEnd = resources.Food,
                waterAtEnd = resources.Water,
                snacksEaten = resources.SnacksEaten
            };
            foreach (GooseLossReason reason in System.Enum.GetValues(typeof(GooseLossReason)))
            {
                result.SetLost(reason, flock.GetLostThisLeg(reason));
            }

            if (GameFlowManager.Instance != null)
            {
                GameFlowManager.Instance.CompleteLeg(result);
            }
            else
            {
                Debug.LogWarning("[LegProgressTracker] No GameFlowManager; leg result not reported.");
            }
        }
    }
}
