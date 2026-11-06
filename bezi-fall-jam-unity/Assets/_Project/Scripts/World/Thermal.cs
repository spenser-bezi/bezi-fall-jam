using FallIsLife.Data;
using FallIsLife.Flight;

namespace FallIsLife.World
{
    /// <summary>Rising warm air over fields: free climb and drain paused briefly (GDD §5.7). Leader only.</summary>
    public class Thermal : Pickup
    {
        /// <inheritdoc />
        public override PickupType Type => PickupType.Thermal;

        /// <inheritdoc />
        protected override bool Collect(GooseAgent goose)
        {
            goose.Flock.ApplyThermal(Amount);
            return true;
        }
    }
}
