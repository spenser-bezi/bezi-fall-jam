using UnityEngine;

namespace FallIsLife.Core
{
    /// <summary>
    /// Play-from-any-scene support. If GameSystems is missing after the first scene loads
    /// (e.g. pressing Play in Flight.unity or a Sandbox scene), it is spawned automatically.
    /// GameFlowManager then builds a debug RunState so the scene runs standalone.
    /// </summary>
    public static class Bootstrapper
    {
        /// <summary>Asset path of the GameSystems prefab (editor-only lookup; builds always start in Boot).</summary>
        public const string GameSystemsPrefabPath = "Assets/_Project/Prefabs/Systems/GameSystems.prefab";

        /// <summary>Spawns GameSystems if no GameFlowManager exists yet.</summary>
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        public static void EnsureGameSystems()
        {
            if (GameFlowManager.Instance != null || Object.FindFirstObjectByType<GameFlowManager>() != null)
            {
                return;
            }

#if UNITY_EDITOR
            var prefab = UnityEditor.AssetDatabase.LoadAssetAtPath<GameObject>(GameSystemsPrefabPath);
            if (prefab == null)
            {
                Debug.LogWarning($"[Bootstrapper] GameSystems prefab not found at {GameSystemsPrefabPath}.");
                return;
            }
            GameObject instance = Object.Instantiate(prefab);
            instance.name = prefab.name;
#endif
        }
    }
}
