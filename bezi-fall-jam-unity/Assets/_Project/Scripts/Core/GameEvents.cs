using System;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.Core
{
    /// <summary>
    /// Global game events (contract, see Foundation plan section 4).
    /// Prefer adding new events over renaming or removing existing ones.
    /// </summary>
    public static class GameEvents
    {
        public static event Action<GamePhase> PhaseChanged;
        public static event Action<int> FlockSizeChanged;
        public static event Action<GooseLossReason> GooseLost;
        public static event Action GooseRecruited;
        public static event Action<ResourceType, float> ResourceChanged;
        public static event Action<float> LegProgressChanged;
        public static event Action<LegResult> LegCompleted;
        public static event Action<string, Vector3> HazardWarning;
        public static event Action<bool> HonkPerformed;
        public static event Action<PickupType> PickupCollected;

        /// <summary>Clears all subscribers so stale listeners never survive a play session without a domain reload.</summary>
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        public static void ClearAllSubscribers()
        {
            PhaseChanged = null;
            FlockSizeChanged = null;
            GooseLost = null;
            GooseRecruited = null;
            ResourceChanged = null;
            LegProgressChanged = null;
            LegCompleted = null;
            HazardWarning = null;
            HonkPerformed = null;
            PickupCollected = null;
        }

        /// <summary>Raises <see cref="PhaseChanged"/> after a phase scene finished loading.</summary>
        public static void RaisePhaseChanged(GamePhase phase) => PhaseChanged?.Invoke(phase);

        /// <summary>Raises <see cref="FlockSizeChanged"/> with the new flock size.</summary>
        public static void RaiseFlockSizeChanged(int newSize) => FlockSizeChanged?.Invoke(newSize);

        /// <summary>Raises <see cref="GooseLost"/> when a goose leaves the flock.</summary>
        public static void RaiseGooseLost(GooseLossReason reason) => GooseLost?.Invoke(reason);

        /// <summary>Raises <see cref="GooseRecruited"/> when a goose joins the flock.</summary>
        public static void RaiseGooseRecruited() => GooseRecruited?.Invoke();

        /// <summary>Raises <see cref="ResourceChanged"/> with a normalized (0-1) meter value.</summary>
        public static void RaiseResourceChanged(ResourceType type, float normalizedValue) => ResourceChanged?.Invoke(type, normalizedValue);

        /// <summary>Raises <see cref="LegProgressChanged"/> with normalized leg progress (0-1).</summary>
        public static void RaiseLegProgressChanged(float normalizedProgress) => LegProgressChanged?.Invoke(normalizedProgress);

        /// <summary>Raises <see cref="LegCompleted"/> when a leg ends (landed or flock lost).</summary>
        public static void RaiseLegCompleted(LegResult result) => LegCompleted?.Invoke(result);

        /// <summary>Raises <see cref="HazardWarning"/> so the HUD can show a telegraph (e.g. "TRAFFIC").</summary>
        public static void RaiseHazardWarning(string label, Vector3 worldPosition) => HazardWarning?.Invoke(label, worldPosition);

        /// <summary>Raises <see cref="HonkPerformed"/>. True means a hold (tighten) started, false means a tap.</summary>
        public static void RaiseHonkPerformed(bool isHoldStart) => HonkPerformed?.Invoke(isHoldStart);

        /// <summary>Raises <see cref="PickupCollected"/> when the flock collects a pickup.</summary>
        public static void RaisePickupCollected(PickupType type) => PickupCollected?.Invoke(type);
    }
}
