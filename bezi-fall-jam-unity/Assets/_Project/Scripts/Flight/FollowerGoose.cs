using FallIsLife.Core;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Follower behaviour: SmoothDamp toward its V slot, drift away while straggling (GDD §5.5),
    /// and fly off when leaving the flock ("joined another flock").
    /// </summary>
    [RequireComponent(typeof(GooseAgent))]
    public class FollowerGoose : MonoBehaviour
    {
        private const float StragglerRollAmplitude = 35f;
        private const float StragglerRollFrequency = 5f;
        private const float BankFromLateralSpeedDivisor = 10f;
        private const float MaxVisualBankAngle = 25f;

        private GooseAgent agent;
        private FlockController flock;
        private FlockBalance balance;
        private Vector3 slotOffset;
        private Vector3 smoothVelocity;
        private Vector3 stragglerOffset;
        private float stragglerSide;
        private Vector3 leaveDirection;
        private float leaveTimeRemaining;
        private Vector3 lastPosition;

        public GooseAgent Agent => agent;
        public GooseState State => agent.State;

        /// <summary>Seconds left before this straggler is lost (0 when not straggling).</summary>
        public float StragglerTimeRemaining { get; private set; }

        /// <summary>Straggler time left as 0-1 (1 = just started straggling).</summary>
        public float StragglerTimeNormalized => balance != null && balance.stragglerDuration > 0f ? StragglerTimeRemaining / balance.stragglerDuration : 0f;

        private void Awake()
        {
            agent = GetComponent<GooseAgent>();
        }

        /// <summary>Links the follower to its flock. Called by FlockController on spawn.</summary>
        public void Initialize(FlockController owner, FlockBalance flockBalance)
        {
            flock = owner;
            balance = flockBalance;
            agent.Initialize(owner);
            lastPosition = transform.position;
        }

        /// <summary>Sets the slot offset relative to the leader (world axes; the flock always faces +Z).</summary>
        public void SetSlotOffset(Vector3 offset)
        {
            slotOffset = offset;
        }

        /// <summary>Knocks the follower out of formation for the straggler duration.</summary>
        public void BeginStraggling()
        {
            if (agent.State != GooseState.InFormation)
            {
                return;
            }
            agent.SetState(GooseState.Straggling);
            StragglerTimeRemaining = balance.stragglerDuration;
            stragglerOffset = Vector3.zero;
            stragglerSide = slotOffset.x >= 0f ? 1f : -1f;
            agent.AnimationDriver?.TriggerTumble();
        }

        /// <summary>Returns a straggler to its slot (honk recall or proximity).</summary>
        public void Rejoin()
        {
            if (agent.State != GooseState.Straggling)
            {
                return;
            }
            agent.SetState(GooseState.InFormation);
            StragglerTimeRemaining = 0f;
            stragglerOffset = Vector3.zero;
        }

        /// <summary>Flies off and despawns ("joined another flock").</summary>
        public void BeginLeaving()
        {
            agent.SetState(GooseState.Leaving);
            StragglerTimeRemaining = 0f;
            leaveTimeRemaining = balance.leaveDuration;
            float side = slotOffset.x >= 0f ? 1f : -1f;
            leaveDirection = new Vector3(side, 1f, -1f).normalized;
        }

        private void Update()
        {
            if (flock == null)
            {
                return;
            }

            float deltaTime = Time.deltaTime;
            switch (agent.State)
            {
                case GooseState.InFormation:
                    MoveTowardSlot(deltaTime);
                    break;
                case GooseState.Straggling:
                    UpdateStraggling(deltaTime);
                    break;
                case GooseState.Leaving:
                    UpdateLeaving(deltaTime);
                    break;
            }
            UpdateVisuals(deltaTime);
            lastPosition = transform.position;
        }

        private void MoveTowardSlot(float deltaTime)
        {
            Vector3 target = flock.LeaderPosition + slotOffset;
            transform.position = Vector3.SmoothDamp(transform.position, target, ref smoothVelocity, balance.followerSmoothTime, Mathf.Infinity, deltaTime);
        }

        private void UpdateStraggling(float deltaTime)
        {
            stragglerOffset += new Vector3(stragglerSide * balance.stragglerDriftOutSpeed, 0f, -balance.stragglerDriftBackSpeed) * deltaTime;
            Vector3 target = flock.LeaderPosition + slotOffset + stragglerOffset;
            transform.position = Vector3.SmoothDamp(transform.position, target, ref smoothVelocity, balance.followerSmoothTime, Mathf.Infinity, deltaTime);

            StragglerTimeRemaining = Mathf.Max(0f, StragglerTimeRemaining - deltaTime);
            if (StragglerTimeRemaining <= 0f)
            {
                flock.HandleStragglerExpired(this);
            }
        }

        private void UpdateLeaving(float deltaTime)
        {
            transform.position += leaveDirection * balance.leaveSpeed * deltaTime;
            leaveTimeRemaining -= deltaTime;
            if (leaveTimeRemaining <= 0f)
            {
                Destroy(gameObject);
            }
        }

        private void UpdateVisuals(float deltaTime)
        {
            if (agent.VisualRoot == null || deltaTime <= 0f)
            {
                return;
            }

            float lateralSpeed = (transform.position.x - lastPosition.x) / deltaTime;
            float bank = Mathf.Clamp(lateralSpeed / BankFromLateralSpeedDivisor, GooseAnimationDriver.MinBank, GooseAnimationDriver.MaxBank);
            float roll = -bank * MaxVisualBankAngle;
            if (agent.State == GooseState.Straggling)
            {
                roll += Mathf.Sin(Time.time * StragglerRollFrequency) * StragglerRollAmplitude;
            }
            agent.VisualRoot.localRotation = Quaternion.Euler(0f, 0f, roll);
            agent.AnimationDriver?.SetBank(bank);
        }
    }
}
