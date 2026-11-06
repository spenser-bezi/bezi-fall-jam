using FallIsLife.Data;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace FallIsLife.Core
{
    /// <summary>
    /// Applies an EnvironmentProfile (fog, ambient, sun, background) to RenderSettings at runtime,
    /// so look-dev never needs to edit scene Lighting settings. Lives on LightingRig_* prefabs.
    /// </summary>
    public class EnvironmentApplier : MonoBehaviour
    {
        [SerializeField] private EnvironmentProfile profile;
        [SerializeField] private Light sun;

        /// <summary>The profile currently applied.</summary>
        public EnvironmentProfile Profile => profile;

        private void OnEnable()
        {
            SceneManager.activeSceneChanged += HandleActiveSceneChanged;
            ApplyRenderSettings();
        }

        private void OnDisable()
        {
            SceneManager.activeSceneChanged -= HandleActiveSceneChanged;
        }

        /// <summary>Re-applies this phase's look once its scene becomes the active scene.</summary>
        private void HandleActiveSceneChanged(Scene previousActiveScene, Scene newActiveScene)
        {
            if (newActiveScene != gameObject.scene)
            {
                return;
            }
            ApplyRenderSettings();
            ApplyCameraBackgrounds();
        }

        private void Start()
        {
            ApplyRenderSettings();
            ApplyCameraBackgrounds();
        }

        /// <summary>Swaps the profile at runtime and re-applies it immediately.</summary>
        public void SetProfile(EnvironmentProfile newProfile)
        {
            profile = newProfile;
            ApplyRenderSettings();
            ApplyCameraBackgrounds();
        }

        private void ApplyRenderSettings()
        {
            if (profile == null)
            {
                return;
            }

            RenderSettings.skybox = null;
            RenderSettings.fog = profile.fogEnabled;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = profile.fogColor;
            RenderSettings.fogDensity = profile.fogDensity;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = profile.ambientSkyColor;
            RenderSettings.ambientEquatorColor = profile.ambientEquatorColor;
            RenderSettings.ambientGroundColor = profile.ambientGroundColor;

            if (sun != null)
            {
                sun.color = profile.sunColor;
                sun.intensity = profile.sunIntensity;
                sun.transform.rotation = Quaternion.Euler(profile.sunRotation);
                RenderSettings.sun = sun;
            }
        }

        private void ApplyCameraBackgrounds()
        {
            if (profile == null)
            {
                return;
            }
            foreach (Camera sceneCamera in FindObjectsByType<Camera>(FindObjectsSortMode.None))
            {
                if (sceneCamera.gameObject.scene != gameObject.scene)
                {
                    continue;
                }
                sceneCamera.clearFlags = CameraClearFlags.SolidColor;
                sceneCamera.backgroundColor = profile.backgroundColor;
            }
        }
    }
}
