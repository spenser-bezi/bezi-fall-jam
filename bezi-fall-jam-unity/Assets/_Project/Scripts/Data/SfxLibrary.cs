using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Named SFX slots. Empty slots are silently skipped by AudioManager.</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Audio/Sfx Library", fileName = "SfxLibrary")]
    public class SfxLibrary : ScriptableObject
    {
        public AudioClip[] honk = new AudioClip[0];
        public AudioClip[] wingFlap = new AudioClip[0];
        public AudioClip gooseLost;
        public AudioClip gooseRecruited;
        public AudioClip pickup;
        public AudioClip hazardWarning;
        public AudioClip stamp;

        /// <summary>Returns a random clip from an array, or null when the array is empty.</summary>
        public static AudioClip PickRandom(AudioClip[] clips)
        {
            if (clips == null || clips.Length == 0)
            {
                return null;
            }
            return clips[Random.Range(0, clips.Length)];
        }
    }
}
