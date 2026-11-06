using FallIsLife.Core;
using FallIsLife.Flight;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>Pause overlay during Flight: Resume or return to the Main Menu.</summary>
    public class PauseMenu : UIScreen
    {
        private const string OverlayName = "pause-overlay";
        private const string ResumeButtonName = "resume-button";
        private const string MenuButtonName = "menu-button";
        private const string HiddenClass = "hidden";

        private VisualElement overlay;
        private bool isShown;

        /// <inheritdoc />
        protected override void BindScreen(VisualElement root)
        {
            overlay = root.Q<VisualElement>(OverlayName);
            BindButton(root, ResumeButtonName, Resume);
            BindButton(root, MenuButtonName, QuitToMenu);
            FlightSceneController.PauseChanged += HandlePauseChanged;
            HandlePauseChanged(false);
        }

        /// <inheritdoc />
        protected override void OnDisable()
        {
            FlightSceneController.PauseChanged -= HandlePauseChanged;
            base.OnDisable();
        }

        /// <inheritdoc />
        protected override void OnSubmit()
        {
            if (isShown)
            {
                Resume();
            }
        }

        private void HandlePauseChanged(bool isPaused)
        {
            isShown = isPaused;
            overlay?.EnableInClassList(HiddenClass, !isPaused);
        }

        private void Resume()
        {
            FlightSceneController.Current?.SetPaused(false);
        }

        private void QuitToMenu()
        {
            FlightSceneController.Current?.SetPaused(false);
            GameFlowManager.Instance?.ReturnToMainMenu();
        }
    }
}
