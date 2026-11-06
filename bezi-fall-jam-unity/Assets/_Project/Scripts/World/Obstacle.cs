using FallIsLife.Data;
using FallIsLife.Flight;
using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>
    /// Base obstacle. Colliders (triggers on the Obstacle layer) live on this logic prefab; a kinematic
    /// Rigidbody on the root gathers child collider triggers. Calls GooseAgent.OnObstacleHit (contract).
    /// </summary>
    public class Obstacle : MonoBehaviour
    {
        [SerializeField] private ObstacleCategory category;

        public ObstacleCategory Category => category;
        public ObstacleDefinition Definition { get; private set; }
        protected Transform Target { get; private set; }

        /// <summary>Called by ObstacleSpawner right after spawning.</summary>
        public virtual void Initialize(ObstacleDefinition definition, Transform target)
        {
            Definition = definition;
            Target = target;
        }

        protected virtual void OnTriggerEnter(Collider other)
        {
            GooseAgent goose = other.GetComponentInParent<GooseAgent>();
            if (goose != null)
            {
                OnGooseEnter(goose);
            }
        }

        protected virtual void OnTriggerExit(Collider other)
        {
            GooseAgent goose = other.GetComponentInParent<GooseAgent>();
            if (goose != null)
            {
                OnGooseExit(goose);
            }
        }

        /// <summary>Default behaviour: hit the goose. Override for zones.</summary>
        protected virtual void OnGooseEnter(GooseAgent goose)
        {
            goose.OnObstacleHit(this);
        }

        /// <summary>Called when a goose leaves the trigger. No-op by default.</summary>
        protected virtual void OnGooseExit(GooseAgent goose)
        {
        }
    }
}
