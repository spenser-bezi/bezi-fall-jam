using FallIsLife.Data;
using FallIsLife.Flight;
using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>A lone goose circling with a soft glow: +1 flock (GDD §5.7).</summary>
    public class LostGoosePickup : Pickup
    {
        private const float FullTurnRadians = Mathf.PI * 2f;

        [SerializeField] private Transform circlingVisual;
        [SerializeField] private float circleRadius = 2.5f;
        [SerializeField] private float circleSpeed = 0.35f;

        /// <inheritdoc />
        public override PickupType Type => PickupType.LostGoose;

        private void Update()
        {
            if (circlingVisual == null)
            {
                return;
            }
            float angle = Time.time * circleSpeed * FullTurnRadians;
            circlingVisual.localPosition = new Vector3(Mathf.Cos(angle), 0f, Mathf.Sin(angle)) * circleRadius;
            circlingVisual.localRotation = Quaternion.LookRotation(new Vector3(-Mathf.Sin(angle), 0f, Mathf.Cos(angle)));
        }

        /// <inheritdoc />
        protected override bool Collect(GooseAgent goose)
        {
            int geeseToAdd = Mathf.Max(1, Mathf.RoundToInt(Amount));
            bool addedAny = false;
            for (int i = 0; i < geeseToAdd; i++)
            {
                addedAny |= goose.Flock.AddGoose();
            }
            return addedAny;
        }
    }
}
