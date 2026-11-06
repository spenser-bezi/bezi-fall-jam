namespace FallIsLife.Core
{
    /// <summary>Physics layer constants. Must match ProjectSettings/TagManager.asset.</summary>
    public static class GameLayers
    {
        public const int Goose = 6;
        public const int Obstacle = 7;
        public const int Pickup = 8;
        public const int Ground = 9;
        public const int HazardZone = 10;

        public const int GooseMask = 1 << Goose;
        public const int ObstacleMask = 1 << Obstacle;
        public const int PickupMask = 1 << Pickup;
        public const int GroundMask = 1 << Ground;
        public const int HazardZoneMask = 1 << HazardZone;
    }
}
