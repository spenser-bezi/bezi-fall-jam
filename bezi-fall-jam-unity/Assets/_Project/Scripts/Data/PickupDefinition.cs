using FallIsLife.Core;
using UnityEngine;

namespace FallIsLife.Data
{
    /// <summary>Spawn rules and effect amount for one pickup type (GDD §5.7).</summary>
    [CreateAssetMenu(menuName = "Fall Is Life/Pickup Definition", fileName = "Pickup_")]
    public class PickupDefinition : ScriptableObject
    {
        public GameObject prefab;
        public PickupType type;
        public AltitudeBand band = AltitudeBand.Low;
        [Tooltip("Food/Water points, geese, or thermal climb meters, depending on type.")]
        public float amount = 1f;
        [Min(0f)] public float weight = 1f;
        [Tooltip("Placed on the ground (Y = 0) instead of floating inside its band.")]
        public bool groundAnchored = true;
    }
}
