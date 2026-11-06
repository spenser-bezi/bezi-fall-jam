using FallIsLife.Core;
using FallIsLife.Data;
using UnityEngine;

namespace FallIsLife.Audio
{
    /// <summary>
    /// Lives on GameSystems. Subscribes to GameEvents and plays clips from SfxLibrary / MusicLibrary.
    /// Empty slots are silently skipped, so look-dev only needs to drop clips into the libraries.
    /// </summary>
    public class AudioManager : MonoBehaviour
    {
        [SerializeField] private SfxLibrary sfxLibrary;
        [SerializeField] private MusicLibrary musicLibrary;
        [Range(0f, 1f)] [SerializeField] private float musicVolume = 0.6f;
        [Range(0f, 1f)] [SerializeField] private float sfxVolume = 0.9f;
        [SerializeField] private float minHonkPitch = 0.9f;
        [SerializeField] private float maxHonkPitch = 1.15f;

        private AudioSource musicSource;
        private AudioSource sfxSource;
        private AudioSource honkSource;

        public SfxLibrary Sfx => sfxLibrary;
        public MusicLibrary Music => musicLibrary;

        private void Awake()
        {
            musicSource = CreateSource(loop: true, musicVolume);
            sfxSource = CreateSource(loop: false, sfxVolume);
            honkSource = CreateSource(loop: false, sfxVolume);
        }

        private void OnEnable()
        {
            GameEvents.PhaseChanged += HandlePhaseChanged;
            GameEvents.HonkPerformed += HandleHonk;
            GameEvents.GooseLost += HandleGooseLost;
            GameEvents.GooseRecruited += HandleGooseRecruited;
            GameEvents.PickupCollected += HandlePickupCollected;
            GameEvents.HazardWarning += HandleHazardWarning;
        }

        private void OnDisable()
        {
            GameEvents.PhaseChanged -= HandlePhaseChanged;
            GameEvents.HonkPerformed -= HandleHonk;
            GameEvents.GooseLost -= HandleGooseLost;
            GameEvents.GooseRecruited -= HandleGooseRecruited;
            GameEvents.PickupCollected -= HandlePickupCollected;
            GameEvents.HazardWarning -= HandleHazardWarning;
        }

        /// <summary>Plays a one-shot clip on the SFX source. Null clips are ignored.</summary>
        public void PlaySfx(AudioClip clip)
        {
            if (clip != null && sfxSource != null)
            {
                sfxSource.PlayOneShot(clip);
            }
        }

        /// <summary>Switches music to a clip (null stops the music).</summary>
        public void PlayMusic(AudioClip clip)
        {
            if (musicSource == null || musicSource.clip == clip)
            {
                return;
            }
            musicSource.Stop();
            musicSource.clip = clip;
            if (clip != null)
            {
                musicSource.Play();
            }
        }

        private void HandlePhaseChanged(GamePhase phase)
        {
            if (musicLibrary != null)
            {
                PlayMusic(musicLibrary.GetMusic(phase));
            }
            if (phase == GamePhase.Flight && sfxLibrary != null)
            {
                PlaySfx(sfxLibrary.stamp);
            }
        }

        private void HandleHonk(bool isHoldStart)
        {
            AudioClip clip = sfxLibrary != null ? SfxLibrary.PickRandom(sfxLibrary.honk) : null;
            if (clip == null || honkSource == null)
            {
                return;
            }
            honkSource.pitch = Random.Range(minHonkPitch, maxHonkPitch);
            honkSource.PlayOneShot(clip);
        }

        private void HandleGooseLost(GooseLossReason reason) => PlaySfx(sfxLibrary != null ? sfxLibrary.gooseLost : null);

        private void HandleGooseRecruited() => PlaySfx(sfxLibrary != null ? sfxLibrary.gooseRecruited : null);

        private void HandlePickupCollected(PickupType type) => PlaySfx(sfxLibrary != null ? sfxLibrary.pickup : null);

        private void HandleHazardWarning(string label, Vector3 worldPosition) => PlaySfx(sfxLibrary != null ? sfxLibrary.hazardWarning : null);

        private AudioSource CreateSource(bool loop, float volume)
        {
            AudioSource source = gameObject.AddComponent<AudioSource>();
            source.playOnAwake = false;
            source.loop = loop;
            source.volume = volume;
            source.spatialBlend = 0f;
            return source;
        }
    }
}
