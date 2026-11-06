using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>Lives on tile logic prefabs. Sockets mark where props and snacks can be placed.</summary>
    public class HexTile : MonoBehaviour
    {
        [SerializeField] private string biomeId;
        [SerializeField] private Transform[] propSockets = new Transform[0];
        [SerializeField] private Transform[] snackSockets = new Transform[0];

        public string BiomeId => biomeId;
        public Transform[] PropSockets => propSockets;
        public Transform[] SnackSockets => snackSockets;
    }
}
