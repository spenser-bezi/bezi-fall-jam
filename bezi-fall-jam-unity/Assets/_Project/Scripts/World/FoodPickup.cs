using FallIsLife.Data;
using FallIsLife.Flight;

namespace FallIsLife.World
{
    /// <summary>Snack patch (corn / apples / pumpkins): +Food (GDD §5.7).</summary>
    public class FoodPickup : Pickup
    {
        /// <inheritdoc />
        public override PickupType Type => PickupType.Food;

        /// <inheritdoc />
        protected override bool Collect(GooseAgent goose)
        {
            if (goose.Flock.Resources == null)
            {
                return false;
            }
            goose.Flock.Resources.AddFood(Amount);
            return true;
        }
    }
}
