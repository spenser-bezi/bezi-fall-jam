using FallIsLife.Core;
using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>
    /// Low-flying plane: waits off to the side, raises the HUD "TRAFFIC" warning, then crosses the corridor
    /// so it arrives as the flock does (GDD §5.8). Speed is estimated from the target's motion.
    /// </summary>
    public class FlyByObstacle : Obstacle
    {
        public const string WarningLabel = "TRAFFIC";
        private const float EvenChance = 0.5f;

        private enum FlyByState { Waiting, Warning, Crossing, Done }

        [SerializeField] private float crossSpeed = 55f;
        [SerializeField] private float warningLeadTime = 2f;
        [Tooltip("Half-width of the crossing path (starts this far to one side, ends on the other).")]
        [SerializeField] private float crossHalfWidth = 95f;
        [Tooltip("Fallback forward speed of the target before it can be measured.")]
        [SerializeField] private float fallbackTargetSpeed = 14f;

        private FlyByState state = FlyByState.Waiting;
        private float direction;
        private float warningTimer;
        private float lastTargetZ;
        private float measuredTargetSpeed;
        private Vector3 crossStart;

        private void Start()
        {
            direction = Random.value < EvenChance ? 1f : -1f;
            crossStart = new Vector3(-direction * crossHalfWidth, transform.position.y, transform.position.z);
            transform.position = crossStart;
            transform.rotation = Quaternion.LookRotation(new Vector3(direction, 0f, 0f));
            measuredTargetSpeed = fallbackTargetSpeed;
            if (Target != null)
            {
                lastTargetZ = Target.position.z;
            }
        }

        private void Update()
        {
            if (Target == null)
            {
                return;
            }

            float deltaTime = Time.deltaTime;
            if (deltaTime > 0f)
            {
                float targetZ = Target.position.z;
                float speed = (targetZ - lastTargetZ) / deltaTime;
                if (speed > 0f)
                {
                    measuredTargetSpeed = speed;
                }
                lastTargetZ = targetZ;
            }

            switch (state)
            {
                case FlyByState.Waiting:
                    UpdateWaiting();
                    break;
                case FlyByState.Warning:
                    warningTimer -= deltaTime;
                    if (warningTimer <= 0f)
                    {
                        state = FlyByState.Crossing;
                    }
                    break;
                case FlyByState.Crossing:
                    transform.position += new Vector3(direction * crossSpeed * deltaTime, 0f, 0f);
                    if (Mathf.Abs(transform.position.x) > crossHalfWidth)
                    {
                        state = FlyByState.Done;
                    }
                    break;
            }
        }

        private void UpdateWaiting()
        {
            float timeUntilTargetArrives = (transform.position.z - Target.position.z) / Mathf.Max(measuredTargetSpeed, Mathf.Epsilon);
            float halfCrossTime = crossSpeed > 0f ? crossHalfWidth / crossSpeed : 0f;
            if (timeUntilTargetArrives <= warningLeadTime + halfCrossTime)
            {
                state = FlyByState.Warning;
                warningTimer = warningLeadTime;
                Vector3 warningPosition = new Vector3(crossStart.x, transform.position.y, transform.position.z);
                GameEvents.RaiseHazardWarning(WarningLabel, warningPosition);
            }
        }
    }
}
