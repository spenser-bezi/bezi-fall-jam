namespace FallIsLife.Flight
{
    /// <summary>Per-goose state. The leader is always InFormation until the flock is gone.</summary>
    public enum GooseState
    {
        InFormation,
        Straggling,
        Leaving
    }
}
