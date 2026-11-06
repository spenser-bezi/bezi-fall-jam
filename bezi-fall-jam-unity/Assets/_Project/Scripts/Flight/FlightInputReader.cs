using FallIsLife.Input;
using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Wraps the generated FallIsLifeControls Flight map. Honk tap vs. hold is decided here in code:
    /// a release before the tap threshold is a tap, holding past it is a hold (tighten).
    /// </summary>
    [DefaultExecutionOrder(ExecutionOrder)]
    public class FlightInputReader : MonoBehaviour
    {
        /// <summary>Runs before gameplay scripts so per-frame honk flags are ready when they are read.</summary>
        public const int ExecutionOrder = -50;
        private const float DefaultTapThreshold = 0.2f;

        private FallIsLifeControls controls;
        private float tapThreshold = DefaultTapThreshold;
        private float honkPressedTime;
        private bool honkIsDown;
        private int honkTappedFrame = -1;
        private int holdStartedFrame = -1;
        private bool inputEnabled = true;

        /// <summary>Steering input: X = lateral, Y = climb/dive.</summary>
        public Vector2 Steer => inputEnabled && controls != null ? Vector2.ClampMagnitude(controls.Flight.Steer.ReadValue<Vector2>(), 1f) : Vector2.zero;

        /// <summary>True on the frame a short honk press was released.</summary>
        public bool HonkTapped => inputEnabled && honkTappedFrame == Time.frameCount;

        /// <summary>True while honk has been held longer than the tap threshold.</summary>
        public bool HonkHeld => inputEnabled && honkIsDown && Time.unscaledTime - honkPressedTime >= tapThreshold;

        /// <summary>True on the frame a hold (tighten) started.</summary>
        public bool HonkHoldStarted => inputEnabled && holdStartedFrame == Time.frameCount;

        /// <summary>True on the frame pause was pressed (works while gameplay input is disabled).</summary>
        public bool PausePressed => controls != null && controls.Flight.Pause.WasPressedThisFrame();

        private void Awake()
        {
            controls = new FallIsLifeControls();
        }

        private void OnEnable()
        {
            controls.Flight.Enable();
        }

        private void OnDisable()
        {
            controls.Flight.Disable();
        }

        private void OnDestroy()
        {
            controls.Dispose();
        }

        /// <summary>Sets the tap/hold threshold in seconds (FlockBalance.honkTapMaxDuration).</summary>
        public void SetTapThreshold(float seconds)
        {
            tapThreshold = Mathf.Max(0f, seconds);
        }

        /// <summary>Enables or disables gameplay input (steer/honk). Pause keeps working.</summary>
        public void SetGameplayInputEnabled(bool isEnabled)
        {
            inputEnabled = isEnabled;
            if (!isEnabled)
            {
                honkIsDown = false;
            }
        }

        private void Update()
        {
            if (controls.Flight.Honk.WasPressedThisFrame())
            {
                honkIsDown = true;
                honkPressedTime = Time.unscaledTime;
                holdStartedFrame = -1;
            }

            if (honkIsDown && holdStartedFrame < 0 && Time.unscaledTime - honkPressedTime >= tapThreshold)
            {
                holdStartedFrame = Time.frameCount;
            }

            if (controls.Flight.Honk.WasReleasedThisFrame() && honkIsDown)
            {
                honkIsDown = false;
                if (Time.unscaledTime - honkPressedTime < tapThreshold)
                {
                    honkTappedFrame = Time.frameCount;
                }
            }
        }
    }
}
