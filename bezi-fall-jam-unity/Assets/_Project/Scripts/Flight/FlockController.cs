using System;
using System.Collections.Generic;
using FallIsLife.Core;
using FallIsLife.Data;
using FallIsLife.World;
using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Spawns the leader and followers, lays out V slots (GDD §5.4), handles tightening, honk/proximity
    /// straggler recall, collisions (GDD §5.5), and adding/losing geese. The leader is always lost last.
    /// </summary>
    public class FlockController : MonoBehaviour
    {
        [SerializeField] private GooseAgent leaderPrefab;
        [SerializeField] private FollowerGoose followerPrefab;

        private readonly List<FollowerGoose> followers = new List<FollowerGoose>();
        private readonly int[] lostThisLeg = new int[Enum.GetValues(typeof(GooseLossReason)).Length];
        private FlockBalance flockBalance;
        private FlightBalance flightBalance;
        private FlightInputReader input;
        private LeaderGooseController leader;
        private float spacingMultiplier = 1f;
        private float spacingVelocity;
        private bool leaderLost;

        /// <summary>Raised once when the last goose (the leader) leaves.</summary>
        public event Action FlockEmptied;

        public LeaderGooseController Leader => leader;
        public FlockResources Resources { get; private set; }
        public IReadOnlyList<FollowerGoose> Followers => followers;
        public Vector3 LeaderPosition => leader != null ? leader.transform.position : transform.position;

        /// <summary>Geese currently in the flock (leader + followers, stragglers included).</summary>
        public int FlockSize => (leaderLost ? 0 : 1) + CountFollowersNotLeaving();

        public int StartingSize { get; private set; }
        public int RecruitsThisLeg { get; private set; }

        /// <summary>Spawns the flock at a start position and wires the leader. Called by FlightSceneController.</summary>
        public void Initialize(FlockBalance flock, FlightBalance flight, FlightInputReader inputReader, FlockResources resources,
            int flockSize, Vector3 startPosition, float windSpeed, float jetStreamBonus)
        {
            flockBalance = flock;
            flightBalance = flight;
            input = inputReader;
            Resources = resources;
            input.SetTapThreshold(flockBalance.honkTapMaxDuration);

            GooseAgent leaderAgent = Instantiate(leaderPrefab, startPosition, Quaternion.identity, transform);
            leaderAgent.name = leaderPrefab.name;
            leaderAgent.Initialize(this);
            leader = leaderAgent.GetComponent<LeaderGooseController>();
            leader.Initialize(flightBalance, input, windSpeed, jetStreamBonus);

            int followerCount = Mathf.Clamp(flockSize - 1, 0, flockBalance.maxFlockSize - 1);
            for (int i = 0; i < followerCount; i++)
            {
                Vector3 slotOffset = CalculateSlotOffset(i, spacingMultiplier);
                SpawnFollower(startPosition + slotOffset);
            }
            RefreshSlots();

            StartingSize = FlockSize;
            GameEvents.RaiseFlockSizeChanged(FlockSize);
        }

        /// <summary>Adds one goose to the back of the V (Lost Goose pickup / recruit). Returns false at max size.</summary>
        public bool AddGoose()
        {
            if (leaderLost || FlockSize >= flockBalance.maxFlockSize)
            {
                return false;
            }
            Vector3 spawnPosition = LeaderPosition + Vector3.back * flockBalance.recruitSpawnBackDistance;
            SpawnFollower(spawnPosition);
            RefreshSlots();
            RecruitsThisLeg++;
            GameEvents.RaiseGooseRecruited();
            GameEvents.RaiseFlockSizeChanged(FlockSize);
            return true;
        }

        /// <summary>Loses the rearmost goose for a reason (e.g. starvation). The leader goes last.</summary>
        public void LoseGoose(GooseLossReason reason)
        {
            FollowerGoose rearmost = FindRearmostFollower(includeStragglers: true);
            if (rearmost != null)
            {
                LoseFollower(rearmost, reason);
                return;
            }
            if (!leaderLost)
            {
                LoseLeader(reason);
            }
        }

        /// <summary>Thermal helper for pickups: free climb plus a temporary drain pause (GDD §5.7).</summary>
        public void ApplyThermal(float climbMeters)
        {
            if (leader == null)
            {
                return;
            }
            leader.ApplyThermalLift(climbMeters);
            Resources?.PauseDrainFor(flightBalance.thermalDuration);
        }

        /// <summary>Returns how many geese were lost this leg for a reason.</summary>
        public int GetLostThisLeg(GooseLossReason reason) => lostThisLeg[(int)reason];

        /// <summary>Called by GooseAgent when an obstacle hits a goose.</summary>
        public void HandleGooseHit(GooseAgent goose, Obstacle obstacle)
        {
            if (goose.IsLeader)
            {
                if (leader.IsWobbling)
                {
                    return;
                }
                leader.BeginWobble();
                for (int i = 0; i < flockBalance.leaderHitStragglerCount; i++)
                {
                    FindRearmostFollower(includeStragglers: false)?.BeginStraggling();
                }
                return;
            }

            FollowerGoose follower = goose.GetComponent<FollowerGoose>();
            if (follower != null)
            {
                follower.BeginStraggling();
            }
        }

        /// <summary>Called by FollowerGoose when its straggler timer runs out.</summary>
        public void HandleStragglerExpired(FollowerGoose follower)
        {
            LoseFollower(follower, GooseLossReason.Straggled);
        }

        private void Update()
        {
            if (leader == null || leaderLost)
            {
                return;
            }

            float targetSpacing = leader.IsTightening ? flockBalance.tightenSpacingMultiplier : 1f;
            spacingMultiplier = Mathf.SmoothDamp(spacingMultiplier, targetSpacing, ref spacingVelocity, flockBalance.spacingSmoothTime);
            RefreshSlots();

            if (input.HonkHoldStarted)
            {
                GameEvents.RaiseHonkPerformed(true);
                leader.Agent.AnimationDriver?.TriggerHonk();
            }
            if (input.HonkTapped)
            {
                GameEvents.RaiseHonkPerformed(false);
                leader.Agent.AnimationDriver?.TriggerHonk();
                RecallStragglers(flockBalance.honkRecallRadius);
            }
            RecallStragglers(flockBalance.proximityRecallRadius);
        }

        private void RecallStragglers(float radius)
        {
            float radiusSquared = radius * radius;
            Vector3 leaderPosition = LeaderPosition;
            foreach (FollowerGoose follower in followers)
            {
                if (follower.State != GooseState.Straggling)
                {
                    continue;
                }
                if ((follower.transform.position - leaderPosition).sqrMagnitude <= radiusSquared)
                {
                    follower.Rejoin();
                }
            }
        }

        private void SpawnFollower(Vector3 position)
        {
            FollowerGoose follower = Instantiate(followerPrefab, position, Quaternion.identity, transform);
            follower.name = followerPrefab.name;
            follower.Initialize(this, flockBalance);
            followers.Add(follower);
        }

        private void LoseFollower(FollowerGoose follower, GooseLossReason reason)
        {
            if (follower == null || follower.State == GooseState.Leaving)
            {
                return;
            }
            followers.Remove(follower);
            follower.BeginLeaving();
            RefreshSlots();
            RecordLoss(reason);
        }

        private void LoseLeader(GooseLossReason reason)
        {
            leaderLost = true;
            leader.DisableControls();
            leader.Agent.SetState(GooseState.Leaving);
            RecordLoss(reason);
            FlockEmptied?.Invoke();
        }

        private void RecordLoss(GooseLossReason reason)
        {
            lostThisLeg[(int)reason]++;
            GameEvents.RaiseGooseLost(reason);
            GameEvents.RaiseFlockSizeChanged(FlockSize);
        }

        private FollowerGoose FindRearmostFollower(bool includeStragglers)
        {
            for (int i = followers.Count - 1; i >= 0; i--)
            {
                FollowerGoose follower = followers[i];
                if (follower.State == GooseState.InFormation || (includeStragglers && follower.State == GooseState.Straggling))
                {
                    return follower;
                }
            }
            return null;
        }

        private int CountFollowersNotLeaving()
        {
            int count = 0;
            foreach (FollowerGoose follower in followers)
            {
                if (follower.State != GooseState.Leaving)
                {
                    count++;
                }
            }
            return count;
        }

        private void RefreshSlots()
        {
            for (int i = 0; i < followers.Count; i++)
            {
                followers[i].SetSlotOffset(CalculateSlotOffset(i, spacingMultiplier));
            }
        }

        /// <summary>Slot i alternates right/left arms; rank grows every two slots.</summary>
        private Vector3 CalculateSlotOffset(int slotIndex, float multiplier)
        {
            const int GeesePerRank = 2;
            int rank = slotIndex / GeesePerRank + 1;
            float side = slotIndex % GeesePerRank == 0 ? 1f : -1f;
            return new Vector3(
                side * rank * flockBalance.wideLateralSpacing * multiplier,
                0f,
                -rank * flockBalance.wideBackSpacing * multiplier);
        }
    }
}
