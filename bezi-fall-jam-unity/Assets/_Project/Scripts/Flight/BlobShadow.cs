using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Keeps a blob shadow on the ground plane under its parent goose and shrinks it with altitude,
    /// so altitude is readable (GDD §5.3). The visual itself is the nested BlobShadow prefab (WS6).
    /// </summary>
    public class BlobShadow : MonoBehaviour
    {
        [SerializeField] private float groundHeight = 0.05f;
        [SerializeField] private float lowAltitude = 4f;
        [SerializeField] private float highAltitude = 40f;
        [SerializeField] private float scaleAtLowAltitude = 2.4f;
        [SerializeField] private float scaleAtHighAltitude = 1.2f;

        private void LateUpdate()
        {
            Transform parent = transform.parent;
            if (parent == null)
            {
                return;
            }

            Vector3 parentPosition = parent.position;
            transform.position = new Vector3(parentPosition.x, groundHeight, parentPosition.z);
            transform.rotation = Quaternion.identity;

            float altitudeFactor = Mathf.InverseLerp(lowAltitude, highAltitude, parentPosition.y);
            float scale = Mathf.Lerp(scaleAtLowAltitude, scaleAtHighAltitude, altitudeFactor);
            transform.localScale = Vector3.one * scale;
        }
    }
}
