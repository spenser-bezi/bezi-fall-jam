using FallIsLife.Data;
using FallIsLife.Flight;

namespace FallIsLife.World
{
    /// <summary>Pond / river splash: +Water (GDD §5.7).</summary>
    public class WaterPickup : Pickup
    {
        /// <inheritdoc />
        public override PickupType Type => PickupType.Water;

        /// <inheritdoc />
        protected override bool Collect(GooseAgent goose)
        {
            if (goose.Flock.Resources == null)
            {
                return false;
            }
            goose.Flock.Resources.AddWater(Amount);
            return true;
        }
    }
}
