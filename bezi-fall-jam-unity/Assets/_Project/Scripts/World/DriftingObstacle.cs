using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>Hot air balloon: drifts slowly sideways and up/down around its spawn point.</summary>
    public class DriftingObstacle : Obstacle
    {
        private const float FullTurnRadians = Mathf.PI * 2f;

        [SerializeField] private float lateralAmplitude = 8f;
        [SerializeField] private float lateralFrequency = 0.12f;
        [SerializeField] private float verticalAmplitude = 3f;
        [SerializeField] private float verticalFrequency = 0.2f;

        private Vector3 origin;
        private float phase;

        private void Start()
        {
            origin = transform.position;
            phase = Random.Range(0f, FullTurnRadians);
        }

        private void Update()
        {
            float time = Time.time;
            float lateral = Mathf.Sin(time * lateralFrequency * FullTurnRadians + phase) * lateralAmplitude;
            float vertical = Mathf.Sin(time * verticalFrequency * FullTurnRadians + phase) * verticalAmplitude;
            transform.position = origin + new Vector3(lateral, vertical, 0f);
        }
    }
}
