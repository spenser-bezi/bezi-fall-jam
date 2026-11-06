namespace FallIsLife.Core
{
    /// <summary>Scene name constants. Must match the build scene list.</summary>
    public static class SceneNames
    {
        public const string Boot = "Boot";
        public const string MainMenu = "MainMenu";
        public const string RoutePlanning = "RoutePlanning";
        public const string Flight = "Flight";
        public const string Night = "Night";
        public const string Results = "Results";

        /// <summary>Returns the phase scene name for a game phase.</summary>
        public static string ForPhase(GamePhase phase)
        {
            switch (phase)
            {
                case GamePhase.MainMenu: return MainMenu;
                case GamePhase.RoutePlanning: return RoutePlanning;
                case GamePhase.Flight: return Flight;
                case GamePhase.Night: return Night;
                case GamePhase.Results: return Results;
                default: return MainMenu;
            }
        }

        /// <summary>Maps a scene name back to its phase. Returns false for Boot, Sandbox, or unknown scenes.</summary>
        public static bool TryGetPhase(string sceneName, out GamePhase phase)
        {
            switch (sceneName)
            {
                case MainMenu: phase = GamePhase.MainMenu; return true;
                case RoutePlanning: phase = GamePhase.RoutePlanning; return true;
                case Flight: phase = GamePhase.Flight; return true;
                case Night: phase = GamePhase.Night; return true;
                case Results: phase = GamePhase.Results; return true;
                default: phase = GamePhase.MainMenu; return false;
            }
        }
    }
}
