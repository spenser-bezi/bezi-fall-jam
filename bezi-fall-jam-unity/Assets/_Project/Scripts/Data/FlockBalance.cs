using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Flock size, formation, and straggler tuning. Start values from GDD §4, §5.4, §5.5, §9.</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Balance/Flock Balance", fileName = "FlockBalance")]
    public class FlockBalance : ScriptableObject
    {
        [Header("Flock size (GDD §4)")]
        public int startingFlockSize = 12;
        public int maxFlockSize = 21;

        [Header("Formation (GDD §5.4)")]
        public float wideLateralSpacing = 2.2f;
        public float wideBackSpacing = 1.8f;
        public float tightenSpacingMultiplier = 0.45f;
        public float spacingSmoothTime = 0.3f;
        public float followerSmoothTime = 0.25f;

        [Header("Honk (GDD §10)")]
        [Tooltip("Presses shorter than this are taps (recall); longer presses are holds (tighten).")]
        public float honkTapMaxDuration = 0.2f;

        [Header("Stragglers (GDD §5.5)")]
        public float stragglerDuration = 5f;
        public float honkRecallRadius = 25f;
        [Tooltip("Flying this close to a straggler recalls it without honking.")]
        public float proximityRecallRadius = 6f;
        public float stragglerDriftBackSpeed = 3f;
        public float stragglerDriftOutSpeed = 1.5f;
        public int leaderHitStragglerCount = 2;

        [Header("Leaving / joining")]
        public float leaveDuration = 3f;
        public float leaveSpeed = 8f;
        public float recruitSpawnBackDistance = 15f;

        [Header("Scoring (GDD §9)")]
        public int twoStarMinGeese = 8;
        public int maxStars = 3;
    }
}
