using FallIsLife.Core;
using FallIsLife.Data;
using FallIsLife.Flight;
using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>
    /// Base pickup: a trigger on the Pickup layer. Collecting calls FlockController / FlockResources public
    /// methods through the goose's flock (interaction contract) and raises GameEvents.PickupCollected.
    /// </summary>
    public abstract class Pickup : MonoBehaviour
    {
        [SerializeField] private float amount = 1f;
        [Tooltip("Only the leader can trigger this pickup.")]
        [SerializeField] private bool leaderOnly;
        [SerializeField] private bool destroyOnCollect = true;

        private bool isCollected;

        /// <summary>The pickup kind, used for events and audio.</summary>
        public abstract PickupType Type { get; }

        /// <summary>Effect amount (food/water points, geese, or climb meters).</summary>
        public float Amount => amount;

        /// <summary>Called by PickupSpawner right after spawning to apply data values.</summary>
        public virtual void Initialize(PickupDefinition definition)
        {
            if (definition != null)
            {
                amount = definition.amount;
            }
        }

        /// <summary>Unity trigger callback; forwards valid geese to <see cref="Collect"/>.</summary>
        protected virtual void OnTriggerEnter(Collider other)
        {
            if (isCollected)
            {
                return;
            }
            GooseAgent goose = other.GetComponentInParent<GooseAgent>();
            if (goose == null || !goose.IsActiveInFlock || (leaderOnly && !goose.IsLeader))
            {
                return;
            }
            if (!Collect(goose))
            {
                return;
            }

            isCollected = true;
            GameEvents.RaisePickupCollected(Type);
            if (destroyOnCollect)
            {
                Destroy(gameObject);
            }
        }

        /// <summary>Applies the effect. Return false to leave the pickup in place (e.g. flock is full).</summary>
        protected abstract bool Collect(GooseAgent goose);
    }
}
