using FallIsLife.World;
using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Shared by leader and follower prefabs. Obstacles call <see cref="OnObstacleHit"/>; pickups use
    /// <see cref="Flock"/> to reach FlockController / FlockResources public methods (interaction contract).
    /// </summary>
    public class GooseAgent : MonoBehaviour
    {
        [SerializeField] private bool isLeader;
        [Tooltip("Parent of the nested *_Visual prefab. Rotated for bank and tumble.")]
        [SerializeField] private Transform visualRoot;
        [SerializeField] private GooseAnimationDriver animationDriver;

        public bool IsLeader => isLeader;
        public GooseState State { get; private set; } = GooseState.InFormation;
        public FlockController Flock { get; private set; }
        public Transform VisualRoot => visualRoot;
        public GooseAnimationDriver AnimationDriver => animationDriver;

        /// <summary>True when this goose can collide with obstacles and collect pickups.</summary>
        public bool IsActiveInFlock => Flock != null && State == GooseState.InFormation;

        /// <summary>Links this goose to its flock. Called by FlockController on spawn.</summary>
        public void Initialize(FlockController flock)
        {
            Flock = flock;
            State = GooseState.InFormation;
        }

        /// <summary>Updates the goose state. Called by FlockController / FollowerGoose.</summary>
        public void SetState(GooseState newState)
        {
            State = newState;
        }

        /// <summary>Entry point for obstacles (contract). Ignored while straggling or leaving.</summary>
        public void OnObstacleHit(Obstacle obstacle)
        {
            if (!IsActiveInFlock)
            {
                return;
            }
            Flock.HandleGooseHit(this, obstacle);
        }
    }
}
