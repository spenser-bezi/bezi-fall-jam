using FallIsLife.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>
    /// Night Summary (GDD §6): "Day N complete - X geese made it", lost geese as faded icons, Food/Water
    /// tick-up, trait effects, then Continue to Route Planning (auto-continues after a while).
    /// </summary>
    public class NightSummaryScreen : UIScreen
    {
        private const string TitleName = "night-title";
        private const string SubtitleName = "night-subtitle";
        private const string GeeseIconsName = "geese-icons";
        private const string FoodFillName = "food-fill";
        private const string WaterFillName = "water-fill";
        private const string FoodValueName = "food-value";
        private const string WaterValueName = "water-value";
        private const string TraitMessagesName = "trait-messages";
        private const string ContinueButtonName = "continue-button";
        private const string TraitMessageClass = "night__trait-message";

        [SerializeField] private float tickUpDuration = 1.5f;
        [SerializeField] private float autoContinueDelay = 10f;

        private NightReport report;
        private float maxMeter;
        private VisualElement foodFill;
        private VisualElement waterFill;
        private Label foodValue;
        private Label waterValue;
        private float elapsed;
        private bool hasContinued;

        /// <inheritdoc />
        protected override void BindScreen(VisualElement root)
        {
            elapsed = 0f;
            hasContinued = false;
            GameFlowManager flowManager = GameFlowManager.Instance;
            report = flowManager != null && flowManager.RunState != null ? flowManager.RunState.LastNight : null;
            maxMeter = flowManager != null ? flowManager.ResourceBalance.maxMeter : 0f;

            foodFill = root.Q<VisualElement>(FoodFillName);
            waterFill = root.Q<VisualElement>(WaterFillName);
            foodValue = root.Q<Label>(FoodValueName);
            waterValue = root.Q<Label>(WaterValueName);
            BindButton(root, ContinueButtonName, Continue);

            if (report == null)
            {
                Debug.LogWarning("[NightSummaryScreen] No night report available.");
                return;
            }

            root.Q<Label>(TitleName).text = $"Day {report.dayCompleted} complete - {report.geeseArrived} geese made it";
            root.Q<Label>(SubtitleName).text = $"Resting at {report.lakeName}";
            int lostOnLeg = Mathf.Max(0, report.geeseStartedLeg - report.geeseArrived);
            UIFormat.FillGooseIcons(root.Q<VisualElement>(GeeseIconsName), report.geeseArrived + report.geeseRecruited, lostOnLeg);

            VisualElement traitMessages = root.Q<VisualElement>(TraitMessagesName);
            traitMessages.Clear();
            foreach (string message in report.traitMessages)
            {
                traitMessages.Add(UIFormat.Label(message, TraitMessageClass));
            }
            ApplyMeters(0f);
        }

        /// <inheritdoc />
        protected override void Update()
        {
            base.Update();
            if (report == null || hasContinued)
            {
                return;
            }
            elapsed += Time.deltaTime;
            ApplyMeters(tickUpDuration > 0f ? Mathf.Clamp01(elapsed / tickUpDuration) : 1f);
            if (elapsed >= autoContinueDelay)
            {
                Continue();
            }
        }

        /// <inheritdoc />
        protected override void OnSubmit()
        {
            Continue();
        }

        private void ApplyMeters(float progress)
        {
            if (maxMeter <= 0f)
            {
                return;
            }
            float food = Mathf.Lerp(report.foodBefore, report.foodAfter, progress);
            float water = Mathf.Lerp(report.waterBefore, report.waterAfter, progress);
            UIFormat.SetFill(foodFill, food / maxMeter);
            UIFormat.SetFill(waterFill, water / maxMeter);
            if (foodValue != null)
            {
                foodValue.text = $"FOOD {Mathf.RoundToInt(food)}";
            }
            if (waterValue != null)
            {
                waterValue.text = $"WATER {Mathf.RoundToInt(water)}";
            }
        }

        private void Continue()
        {
            if (hasContinued || GameFlowManager.Instance == null)
            {
                return;
            }
            hasContinued = true;
            AcceptsInput = false;
            GameFlowManager.Instance.ContinueFromNight();
        }
    }
}
