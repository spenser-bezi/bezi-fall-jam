using FallIsLife.Core;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Leader movement tuning. Start values from GDD §5.2, §5.3, §5.5, §5.7, §5.9.</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Balance/Flight Balance", fileName = "FlightBalance")]
    public class FlightBalance : ScriptableObject
    {
        [Header("Forward (GDD §5.2)")]
        public float baseForwardSpeed = 14f;
        [Tooltip("Max absolute leg wind (m/s). Leg wind is clamped to +/- this value.")]
        public float maxWindModifier = 4f;
        [Tooltip("Lowest forward speed allowed after wind is applied.")]
        public float minForwardSpeed = 6f;

        [Header("Steering (GDD §5.2)")]
        public float lateralSteerSpeed = 10f;
        public float maxBankAngle = 25f;
        public float bankSmoothTime = 0.15f;
        public float climbSpeed = 6f;
        public float minAltitude = 4f;
        public float maxAltitude = 40f;
        public float startAltitude = 8f;

        [Header("Lateral bounds (GDD §5.2)")]
        public float lateralBound = 70f;
        [Tooltip("Width of the soft wall beyond the bound, where the push-back ramps to full strength.")]
        public float softWallWidth = 10f;
        public float softWallPushSpeed = 14f;

        [Header("Altitude bands (GDD §5.3)")]
        public float lowBandMaxAltitude = 12f;
        public float midBandMaxAltitude = 26f;

        [Header("Leg flow (GDD §5.9)")]
        public float takeoffDuration = 2f;
        public float landingDuration = 2f;

        [Header("Leader collision (GDD §5.5)")]
        public float leaderWobbleDuration = 1.5f;
        [Range(0f, 1f)] public float wobbleControlMultiplier = 0.4f;
        public float wobbleRollAmplitude = 20f;
        public float wobbleRollFrequency = 8f;

        [Header("Thermals (GDD §5.7)")]
        [Tooltip("Seconds the thermal climb lasts and drain stays paused.")]
        public float thermalDuration = 2f;

        /// <summary>Returns the altitude band for a height in meters.</summary>
        public AltitudeBand GetBand(float altitude)
        {
            if (altitude < lowBandMaxAltitude)
            {
                return AltitudeBand.Low;
            }
            return altitude < midBandMaxAltitude ? AltitudeBand.Mid : AltitudeBand.High;
        }

        /// <summary>Returns the (min, max) altitude range of a band in meters.</summary>
        public Vector2 GetBandRange(AltitudeBand band)
        {
            switch (band)
            {
                case AltitudeBand.Low: return new Vector2(minAltitude, lowBandMaxAltitude);
                case AltitudeBand.Mid: return new Vector2(lowBandMaxAltitude, midBandMaxAltitude);
                default: return new Vector2(midBandMaxAltitude, maxAltitude);
            }
        }
    }
}
