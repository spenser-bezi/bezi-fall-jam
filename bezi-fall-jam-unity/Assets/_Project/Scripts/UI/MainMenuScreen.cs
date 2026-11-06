using FallIsLife.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>Main Menu: start a new migration or quit.</summary>
    public class MainMenuScreen : UIScreen
    {
        private const string StartButtonName = "start-button";
        private const string QuitButtonName = "quit-button";

        /// <inheritdoc />
        protected override void BindScreen(VisualElement root)
        {
            BindButton(root, StartButtonName, StartRun);
            BindButton(root, QuitButtonName, QuitGame);
        }

        /// <inheritdoc />
        protected override void OnSubmit()
        {
            StartRun();
        }

        private void StartRun()
        {
            if (GameFlowManager.Instance != null && !GameFlowManager.Instance.IsLoading)
            {
                AcceptsInput = false;
                GameFlowManager.Instance.StartNewRun();
            }
        }

        private static void QuitGame()
        {
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit();
#endif
        }
    }
}
