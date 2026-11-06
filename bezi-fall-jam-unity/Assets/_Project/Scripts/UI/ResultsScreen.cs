using FallIsLife.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>
    /// Results (GDD §9): win/lose title, geese arrived of total, losses by cause, snacks eaten, stars,
    /// and the route taken drawn on the chart.
    /// </summary>
    public class ResultsScreen : UIScreen
    {
        private const string TitleName = "results-title";
        private const string SubtitleName = "results-subtitle";
        private const string StarsName = "stars";
        private const string ArrivedName = "arrived-label";
        private const string CollisionsName = "lost-collisions";
        private const string HungerName = "lost-hunger";
        private const string ThirstName = "lost-thirst";
        private const string SnacksName = "snacks-label";
        private const string MapContainerName = "route-map-container";
        private const string PlayAgainButtonName = "play-again-button";
        private const string MenuButtonName = "menu-button";
        private const string StarClass = "star";
        private const string StarEarnedClass = "star--earned";
        private const string WinTitle = "Welcome to Sweet Tea Bayou!";
        private const string LoseTitle = "Your flock found other ways south...";
        private const string LoseSubtitle = "Try again?";

        /// <inheritdoc />
        protected override void BindScreen(VisualElement root)
        {
            BindButton(root, PlayAgainButtonName, PlayAgain);
            BindButton(root, MenuButtonName, ReturnToMenu);

            GameFlowManager flowManager = GameFlowManager.Instance;
            RunState run = flowManager != null ? flowManager.RunState : null;
            if (run == null)
            {
                Debug.LogWarning("[ResultsScreen] No RunState available.");
                return;
            }

            bool won = run.Outcome == RunOutcome.Won;
            string destination = flowManager.RouteMap != null && flowManager.RouteMap.destinationStop != null
                ? flowManager.RouteMap.destinationStop.displayName
                : string.Empty;
            root.Q<Label>(TitleName).text = won ? WinTitle : LoseTitle;
            root.Q<Label>(SubtitleName).text = won ? $"{run.FlockSize} geese splashed down at {destination}" : LoseSubtitle;

            int stars = run.CalculateStars(flowManager.FlockBalance);
            VisualElement starRow = root.Q<VisualElement>(StarsName);
            starRow.Clear();
            for (int i = 0; i < flowManager.FlockBalance.maxStars; i++)
            {
                var star = new VisualElement();
                star.AddToClassList(StarClass);
                star.EnableInClassList(StarEarnedClass, i < stars);
                starRow.Add(star);
            }

            int arrived = won ? run.FlockSize : 0;
            root.Q<Label>(ArrivedName).text = $"Geese arrived: {arrived} / {run.TotalGeeseThisRun}";
            int collisions = run.GetLost(GooseLossReason.Collision) + run.GetLost(GooseLossReason.Straggled);
            root.Q<Label>(CollisionsName).text = $"Lost to collisions: {collisions}";
            root.Q<Label>(HungerName).text = $"Lost to hunger: {run.GetLost(GooseLossReason.Hunger)}";
            root.Q<Label>(ThirstName).text = $"Lost to thirst: {run.GetLost(GooseLossReason.Thirst)}";
            root.Q<Label>(SnacksName).text = $"Snacks eaten: {run.SnacksEaten}";

            VisualElement mapContainer = root.Q<VisualElement>(MapContainerName);
            mapContainer.Clear();
            var mapView = new RouteMapView();
            mapContainer.Add(mapView);
            mapView.SetData(flowManager.RouteMap, run.CurrentStop, null, run.VisitedStops);
        }

        /// <inheritdoc />
        protected override void OnSubmit()
        {
            ReturnToMenu();
        }

        private void PlayAgain()
        {
            AcceptsInput = false;
            GameFlowManager.Instance?.StartNewRun();
        }

        private void ReturnToMenu()
        {
            AcceptsInput = false;
            GameFlowManager.Instance?.ReturnToMainMenu();
        }
    }
}
