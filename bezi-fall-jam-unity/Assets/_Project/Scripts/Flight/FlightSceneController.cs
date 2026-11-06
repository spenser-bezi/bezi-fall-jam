using System;
using FallIsLife.Core;
using FallIsLife.Data;
using FallIsLife.World;
using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Reads RunState when Flight.unity loads and configures the flock, resources, progress tracker,
    /// world generator, and camera. Also owns pausing. Lives on the FlightSystems prefab.
    /// </summary>
    public class FlightSceneController : MonoBehaviour
    {
        private const float PausedTimeScale = 0f;
        private const float NormalTimeScale = 1f;

        [SerializeField] private FlightBalance flightBalance;
        [SerializeField] private FlockBalance flockBalance;
        [SerializeField] private ResourceBalance resourceBalance;
        [SerializeField] private FlightInputReader input;
        [SerializeField] private FlockController flock;
        [SerializeField] private FlockResources resources;
        [SerializeField] private LegProgressTracker progress;

        /// <summary>Raised when pause is toggled (true = paused).</summary>
        public static event Action<bool> PauseChanged;

        /// <summary>The active Flight scene controller (null outside Flight).</summary>
        public static FlightSceneController Current { get; private set; }

        public FlightBalance FlightBalance => flightBalance;
        public FlockController Flock => flock;
        public FlockResources Resources => resources;
        public LegProgressTracker Progress => progress;
        public LeaderGooseController Leader => flock != null ? flock.Leader : null;
        public RunState RunState { get; private set; }
        public LegSettings Leg { get; private set; }
        public bool IsPaused { get; private set; }
        public bool IsReady { get; private set; }

        /// <summary>Clears static state so it never survives a play session without a domain reload.</summary>
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        public static void ResetStatics()
        {
            PauseChanged = null;
            Current = null;
        }

        private void OnEnable()
        {
            Current = this;
        }

        private void OnDisable()
        {
            if (Current == this)
            {
                Current = null;
            }
            if (IsPaused)
            {
                Time.timeScale = NormalTimeScale;
            }
        }

        private void Start()
        {
            GameFlowManager flowManager = GameFlowManager.Instance;
            if (flowManager == null || flowManager.RunState == null || flowManager.RunState.NextStop == null)
            {
                Debug.LogWarning("[FlightSceneController] No RunState/next stop available; flight not started.");
                return;
            }

            RunState = flowManager.RunState;
            RestStopData destination = RunState.NextStop;
            Leg = destination.leg;

            Vector3 startPosition = new Vector3(0f, flightBalance.startAltitude, 0f);
            flock.Initialize(flockBalance, flightBalance, input, resources, RunState.FlockSize, startPosition, Leg.windSpeed, Leg.JetStreamBonus);
            resources.Initialize(resourceBalance, flock, RunState.Food, RunState.Water, Leg.windSpeed);
            progress.Initialize(flightBalance, flock, resources, Leg.distanceMeters, destination.displayName);

            LegWorldGenerator world = FindFirstObjectByType<LegWorldGenerator>();
            if (world != null)
            {
                world.BeginLeg(Leg, flock.Leader.transform);
            }

            FlightCameraRig cameraRig = FindFirstObjectByType<FlightCameraRig>();
            if (cameraRig != null)
            {
                cameraRig.SetTarget(flock.Leader);
            }

            IsReady = true;
        }

        private void Update()
        {
            if (input != null && input.PausePressed && IsReady && !progress.IsCompleted)
            {
                SetPaused(!IsPaused);
            }
        }

        /// <summary>Pauses or resumes the flight (time scale + gameplay input).</summary>
        public void SetPaused(bool isPaused)
        {
            if (IsPaused == isPaused)
            {
                return;
            }
            IsPaused = isPaused;
            Time.timeScale = isPaused ? PausedTimeScale : NormalTimeScale;
            input.SetGameplayInputEnabled(!isPaused);
            PauseChanged?.Invoke(isPaused);
        }
    }
}
