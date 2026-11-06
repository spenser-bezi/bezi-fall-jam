using FallIsLife.Core;
using FallIsLife.Flight;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace FallIsLife.EditorTools
{
    /// <summary>Editor debug tools: open phase scenes, play from Boot, and skip legs in Play mode.</summary>
    public static class FallIsLifeDebugMenu
    {
        private const string MenuRoot = "Fall Is Life/";
        private const string ScenesFolder = "Assets/_Project/Scenes/";
        private const string SceneExtension = ".unity";
        private const int OpenSceneMenuPriority = 0;
        private const int PlayMenuPriority = 20;
        private const int DebugMenuPriority = 40;

        /// <summary>Saves open scenes and enters Play mode starting from Boot.unity (full flow).</summary>
        [MenuItem(MenuRoot + "Play From Boot", false, PlayMenuPriority)]
        public static void PlayFromBoot()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            {
                return;
            }
            EditorSceneManager.playModeStartScene = AssetDatabase.LoadAssetAtPath<SceneAsset>(GetScenePath(SceneNames.Boot));
            EditorApplication.isPlaying = true;
        }

        /// <summary>Clears the Play-from-Boot override so Play starts in the open scene (debug RunState).</summary>
        [MenuItem(MenuRoot + "Play From Open Scene", false, PlayMenuPriority + 1)]
        public static void PlayFromOpenScene()
        {
            EditorSceneManager.playModeStartScene = null;
            EditorApplication.isPlaying = true;
        }

        /// <summary>Opens Boot.unity.</summary>
        [MenuItem(MenuRoot + "Open Scene/Boot", false, OpenSceneMenuPriority)]
        public static void OpenBoot() => OpenScene(SceneNames.Boot);

        /// <summary>Opens MainMenu.unity.</summary>
        [MenuItem(MenuRoot + "Open Scene/Main Menu", false, OpenSceneMenuPriority + 1)]
        public static void OpenMainMenu() => OpenScene(SceneNames.MainMenu);

        /// <summary>Opens RoutePlanning.unity.</summary>
        [MenuItem(MenuRoot + "Open Scene/Route Planning", false, OpenSceneMenuPriority + 2)]
        public static void OpenRoutePlanning() => OpenScene(SceneNames.RoutePlanning);

        /// <summary>Opens Flight.unity.</summary>
        [MenuItem(MenuRoot + "Open Scene/Flight", false, OpenSceneMenuPriority + 3)]
        public static void OpenFlight() => OpenScene(SceneNames.Flight);

        /// <summary>Opens Night.unity.</summary>
        [MenuItem(MenuRoot + "Open Scene/Night", false, OpenSceneMenuPriority + 4)]
        public static void OpenNight() => OpenScene(SceneNames.Night);

        /// <summary>Opens Results.unity.</summary>
        [MenuItem(MenuRoot + "Open Scene/Results", false, OpenSceneMenuPriority + 5)]
        public static void OpenResults() => OpenScene(SceneNames.Results);

        /// <summary>Play mode only: jumps the current flight leg straight to landing.</summary>
        [MenuItem(MenuRoot + "Debug/Complete Current Leg", false, DebugMenuPriority)]
        public static void CompleteCurrentLeg()
        {
            FlightSceneController flight = FlightSceneController.Current;
            if (flight != null && flight.Progress != null)
            {
                flight.Progress.DebugForceArrival();
            }
        }

        /// <summary>Play mode only: removes one goose (rearmost) to test losses and the lose state.</summary>
        [MenuItem(MenuRoot + "Debug/Lose One Goose", false, DebugMenuPriority + 1)]
        public static void LoseOneGoose()
        {
            FlightSceneController flight = FlightSceneController.Current;
            if (flight != null && flight.Flock != null)
            {
                flight.Flock.LoseGoose(GooseLossReason.Collision);
            }
        }

        [MenuItem(MenuRoot + "Debug/Complete Current Leg", true)]
        [MenuItem(MenuRoot + "Debug/Lose One Goose", true)]
        private static bool ValidateFlightDebug() => Application.isPlaying && FlightSceneController.Current != null;

        private static void OpenScene(string sceneName)
        {
            if (EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            {
                EditorSceneManager.OpenScene(GetScenePath(sceneName));
            }
        }

        private static string GetScenePath(string sceneName) => ScenesFolder + sceneName + SceneExtension;
    }
}
