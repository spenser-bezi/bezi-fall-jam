namespace FallIsLife.Data
{
    /// <summary>Leg weather shown on route cards (GDD §7).</summary>
    public enum WeatherType
    {
        Clear,
        Breezy,
        Foggy,
        Stormy
    }

    /// <summary>Obstacle families from GDD §5.8. Traits scale spawn weights per category.</summary>
    public enum ObstacleCategory
    {
        Tree,
        Steeple,
        Windmill,
        PowerLines,
        Balloon,
        Plane,
        StormCloud
    }

    /// <summary>Pickup kinds from GDD §5.7.</summary>
    public enum PickupType
    {
        Food,
        Water,
        LostGoose,
        Thermal
    }
}
