using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Runtime lighting/fog look for a phase, applied by EnvironmentApplier (GDD §12).</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Environment Profile", fileName = "EnvironmentProfile_")]
    public class EnvironmentProfile : ScriptableObject
    {
        [Header("Fog")]
        public bool fogEnabled = true;
        public Color fogColor = Color.white;
        public float fogDensity = 0.003f;

        [Header("Ambient (trilight)")]
        public Color ambientSkyColor = Color.white;
        public Color ambientEquatorColor = Color.gray;
        public Color ambientGroundColor = Color.gray;

        [Header("Sun")]
        public Color sunColor = Color.white;
        public float sunIntensity = 1f;
        public Vector3 sunRotation = new Vector3(40f, -30f, 0f);

        [Header("Camera")]
        public Color backgroundColor = Color.white;
    }
}
