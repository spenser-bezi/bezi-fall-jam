using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Follow camera per GDD §5.1: perspective ~35° FOV, pitched ~50° down, behind and above the leader,
    /// with the leader ~40% from the bottom of the screen, smooth lag, steer drift, and shake on wobble.
    /// </summary>
    public class FlightCameraRig : MonoBehaviour
    {
        private const float ScreenCenterFraction = 0.5f;
        private const float HalfAngleDivisor = 2f;

        [SerializeField] private Camera rigCamera;
        [SerializeField] private float fieldOfView = 35f;
        [SerializeField] private float pitchAngle = 50f;
        [Tooltip("Distance from the camera to the leader along the view ray.")]
        [SerializeField] private float followDistance = 58f;
        [Range(0f, 1f)]
        [SerializeField] private float leaderScreenHeight = 0.4f;
        [SerializeField] private float followSmoothTime = 0.35f;
        [Tooltip("Lateral look-ahead (m) toward the steering direction.")]
        [SerializeField] private float steerDriftDistance = 6f;
        [SerializeField] private float driftSmoothTime = 0.6f;
        [SerializeField] private float shakeAmplitude = 0.6f;
        [SerializeField] private float shakeFrequency = 25f;

        private LeaderGooseController target;
        private Vector3 followVelocity;
        private float drift;
        private float driftVelocity;

        public Camera Camera => rigCamera;

        /// <summary>Starts following a leader and snaps to its position.</summary>
        public void SetTarget(LeaderGooseController leader)
        {
            target = leader;
            if (rigCamera != null)
            {
                rigCamera.fieldOfView = fieldOfView;
            }
            if (target != null)
            {
                transform.position = CalculateDesiredPosition(0f);
                transform.rotation = Quaternion.Euler(pitchAngle, 0f, 0f);
            }
        }

        private void LateUpdate()
        {
            if (target == null)
            {
                return;
            }

            drift = Mathf.SmoothDamp(drift, target.SteerInput * steerDriftDistance, ref driftVelocity, driftSmoothTime);
            Vector3 desired = CalculateDesiredPosition(drift);
            transform.position = Vector3.SmoothDamp(transform.position, desired, ref followVelocity, followSmoothTime);
            transform.rotation = Quaternion.Euler(pitchAngle, 0f, 0f);

            if (rigCamera != null)
            {
                rigCamera.transform.localPosition = target.IsWobbling ? CalculateShakeOffset() : Vector3.zero;
            }
        }

        /// <summary>
        /// Places the camera so the leader projects at <see cref="leaderScreenHeight"/> of the screen:
        /// the ray to the leader is pitched further down than the camera by the matching screen-space angle.
        /// </summary>
        private Vector3 CalculateDesiredPosition(float lateralDrift)
        {
            float halfFovRadians = fieldOfView * Mathf.Deg2Rad / HalfAngleDivisor;
            float offsetFromCenter = (ScreenCenterFraction - leaderScreenHeight) / ScreenCenterFraction;
            float extraPitchDegrees = Mathf.Atan(offsetFromCenter * Mathf.Tan(halfFovRadians)) * Mathf.Rad2Deg;
            float rayPitchRadians = (pitchAngle + extraPitchDegrees) * Mathf.Deg2Rad;

            Vector3 offset = new Vector3(0f, Mathf.Sin(rayPitchRadians), -Mathf.Cos(rayPitchRadians)) * followDistance;
            Vector3 leaderPosition = target.transform.position;
            leaderPosition.x += lateralDrift;
            return leaderPosition + offset;
        }

        private Vector3 CalculateShakeOffset()
        {
            float time = Time.time * shakeFrequency;
            return new Vector3(Mathf.PerlinNoise(time, 0f) - ScreenCenterFraction, Mathf.PerlinNoise(0f, time) - ScreenCenterFraction, 0f) * shakeAmplitude;
        }
    }
}
