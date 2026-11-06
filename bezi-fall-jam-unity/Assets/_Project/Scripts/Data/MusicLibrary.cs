using FallIsLife.Core;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Music per phase. Empty slots are silently skipped by AudioManager.</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Audio/Music Library", fileName = "MusicLibrary")]
    public class MusicLibrary : ScriptableObject
    {
        public AudioClip mainMenu;
        public AudioClip routePlanning;
        public AudioClip flight;
        public AudioClip night;
        public AudioClip results;

        /// <summary>Returns the music clip for a phase (may be null).</summary>
        public AudioClip GetMusic(GamePhase phase)
        {
            switch (phase)
            {
                case GamePhase.MainMenu: return mainMenu;
                case GamePhase.RoutePlanning: return routePlanning;
                case GamePhase.Flight: return flight;
                case GamePhase.Night: return night;
                case GamePhase.Results: return results;
                default: return null;
            }
        }
    }
}
