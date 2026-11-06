using FallIsLife.Core;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Player-controlled lead goose: automatic forward flight along +Z with wind, lateral steering,
    /// climb/dive, soft lateral walls, wobble on collision, thermal lift, and auto-landing (GDD §5.2).
    /// </summary>
    [RequireComponent(typeof(GooseAgent))]
    public class LeaderGooseController : MonoBehaviour
    {
        private const float CruiseFlapSpeed = 1f;
        private const float ClimbFlapBoost = 0.8f;
        private const float GlideFlapReduction = 0.6f;

        private FlightBalance balance;
        private FlightInputReader input;
        private GooseAgent agent;
        private float legWind;
        private float jetStreamBonus;
        private float flightTime;
        private float smoothedBank;
        private float bankVelocity;
        private float wobbleTimeRemaining;
        private float thermalTimeRemaining;
        private float thermalClimbRate;
        private bool controlsEnabled;
        private bool isInitialized;

        /// <summary>Current altitude band (GDD §5.3).</summary>
        public AltitudeBand CurrentBand { get; private set; } = AltitudeBand.Low;

        /// <summary>True while the player holds honk to tighten the V.</summary>
        public bool IsTightening => controlsEnabled && input != null && input.HonkHeld;

        /// <summary>World-space velocity this frame (m/s).</summary>
        public Vector3 Velocity { get; private set; }

        /// <summary>Current forward ground speed (m/s).</summary>
        public float ForwardSpeed => Velocity.z;

        /// <summary>Height above the ground plane in meters.</summary>
        public float Altitude => transform.position.y;

        /// <summary>True during the post-collision wobble.</summary>
        public bool IsWobbling => wobbleTimeRemaining > 0f;

        /// <summary>True once the auto-landing sequence started.</summary>
        public bool IsLanding { get; private set; }

        /// <summary>True while the jet stream bonus is active (High band on a jet-stream leg).</summary>
        public bool IsInJetStream => jetStreamBonus > 0f && CurrentBand == AltitudeBand.High;

        /// <summary>Signed leg wind in m/s (positive = tailwind).</summary>
        public float LegWind => legWind;

        /// <summary>Raw lateral steer input this frame (-1..1), used for camera drift and HUD.</summary>
        public float SteerInput { get; private set; }

        public GooseAgent Agent => agent;

        private void Awake()
        {
            agent = GetComponent<GooseAgent>();
        }

        /// <summary>Configures the leader for a leg. Called by FlockController.</summary>
        public void Initialize(FlightBalance flightBalance, FlightInputReader inputReader, float windSpeed, float jetStream)
        {
            balance = flightBalance;
            input = inputReader;
            legWind = Mathf.Clamp(windSpeed, -balance.maxWindModifier, balance.maxWindModifier);
            jetStreamBonus = jetStream;
            controlsEnabled = true;
            flightTime = 0f;
            isInitialized = true;
            CurrentBand = balance.GetBand(Altitude);
        }

        /// <summary>Starts the 1.5 s collision wobble (reduced control + roll shake).</summary>
        public void BeginWobble()
        {
            wobbleTimeRemaining = balance.leaderWobbleDuration;
            agent.AnimationDriver?.TriggerTumble();
        }

        /// <summary>Adds a free climb of <paramref name="climbMeters"/> spread over the thermal duration.</summary>
        public void ApplyThermalLift(float climbMeters)
        {
            thermalTimeRemaining = balance.thermalDuration;
            thermalClimbRate = balance.thermalDuration > 0f ? climbMeters / balance.thermalDuration : 0f;
        }

        /// <summary>Starts the automatic landing: input off, descend to minimum altitude while gliding forward.</summary>
        public void BeginLanding()
        {
            IsLanding = true;
            controlsEnabled = false;
        }

        /// <summary>Stops all player control (e.g. when the flock is gone).</summary>
        public void DisableControls()
        {
            controlsEnabled = false;
        }

        private void Update()
        {
            if (!isInitialized)
            {
                return;
            }

            float deltaTime = Time.deltaTime;
            flightTime += deltaTime;
            wobbleTimeRemaining = Mathf.Max(0f, wobbleTimeRemaining - deltaTime);

            Vector2 steer = controlsEnabled ? input.Steer : Vector2.zero;
            if (IsWobbling)
            {
                steer *= balance.wobbleControlMultiplier;
            }
            SteerInput = steer.x;

            Vector3 position = transform.position;
            Vector3 velocity = Vector3.zero;

            velocity.z = CalculateForwardSpeed();
            velocity.x = steer.x * balance.lateralSteerSpeed + CalculateSoftWallPush(position.x);
            velocity.y = CalculateVerticalSpeed(steer.y, deltaTime);

            position += velocity * deltaTime;
            float hardBound = balance.lateralBound + balance.softWallWidth;
            position.x = Mathf.Clamp(position.x, -hardBound, hardBound);
            position.y = Mathf.Clamp(position.y, balance.minAltitude, balance.maxAltitude);
            transform.position = position;

            Velocity = velocity;
            CurrentBand = balance.GetBand(position.y);
            UpdateVisuals(steer, deltaTime);
        }

        private float CalculateForwardSpeed()
        {
            float speed = balance.baseForwardSpeed + legWind;
            if (IsInJetStream)
            {
                speed += jetStreamBonus;
            }
            speed = Mathf.Max(balance.minForwardSpeed, speed);

            float takeoffFactor = balance.takeoffDuration > 0f ? Mathf.Clamp01(flightTime / balance.takeoffDuration) : 1f;
            return speed * Mathf.SmoothStep(0f, 1f, takeoffFactor);
        }

        private float CalculateSoftWallPush(float x)
        {
            float overshoot = Mathf.Abs(x) - balance.lateralBound;
            if (overshoot <= 0f)
            {
                return 0f;
            }
            float strength = balance.softWallWidth > 0f ? Mathf.Clamp01(overshoot / balance.softWallWidth) : 1f;
            return -Mathf.Sign(x) * balance.softWallPushSpeed * strength;
        }

        private float CalculateVerticalSpeed(float climbInput, float deltaTime)
        {
            if (IsLanding)
            {
                return -balance.climbSpeed;
            }

            float verticalSpeed = climbInput * balance.climbSpeed;
            if (thermalTimeRemaining > 0f)
            {
                verticalSpeed += thermalClimbRate;
                thermalTimeRemaining = Mathf.Max(0f, thermalTimeRemaining - deltaTime);
            }
            return verticalSpeed;
        }

        private void UpdateVisuals(Vector2 steer, float deltaTime)
        {
            smoothedBank = Mathf.SmoothDamp(smoothedBank, steer.x, ref bankVelocity, balance.bankSmoothTime, Mathf.Infinity, deltaTime);
            float roll = -smoothedBank * balance.maxBankAngle;
            if (IsWobbling)
            {
                roll += Mathf.Sin(Time.time * balance.wobbleRollFrequency) * balance.wobbleRollAmplitude;
            }
            if (agent.VisualRoot != null)
            {
                agent.VisualRoot.localRotation = Quaternion.Euler(0f, 0f, roll);
            }

            GooseAnimationDriver driver = agent.AnimationDriver;
            if (driver != null)
            {
                float flapSpeed = CruiseFlapSpeed + Mathf.Max(0f, steer.y) * ClimbFlapBoost - Mathf.Max(0f, -steer.y) * GlideFlapReduction;
                driver.SetFlapSpeed(flapSpeed);
                driver.SetBank(smoothedBank);
            }
        }
    }
}
