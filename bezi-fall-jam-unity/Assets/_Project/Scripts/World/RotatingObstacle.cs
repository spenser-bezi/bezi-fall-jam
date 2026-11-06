using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>Windmill: spins its BladesPivot around the local Z axis. Time your pass through the gaps.</summary>
    public class RotatingObstacle : Obstacle
    {
        [SerializeField] private Transform bladesPivot;
        [Tooltip("Degrees per second around the pivot's local Z axis.")]
        [SerializeField] private float rotationSpeed = 45f;
        [SerializeField] private bool randomizeStartAngle = true;

        private const float FullTurnDegrees = 360f;

        private void Start()
        {
            if (bladesPivot != null && randomizeStartAngle)
            {
                bladesPivot.Rotate(0f, 0f, Random.Range(0f, FullTurnDegrees), Space.Self);
            }
        }

        private void Update()
        {
            if (bladesPivot != null)
            {
                bladesPivot.Rotate(0f, 0f, rotationSpeed * Time.deltaTime, Space.Self);
            }
        }
    }
}
