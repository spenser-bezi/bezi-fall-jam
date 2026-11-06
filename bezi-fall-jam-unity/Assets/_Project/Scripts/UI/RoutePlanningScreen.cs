using System.Collections.Generic;
using System.Linq;
using FallIsLife.Core;
using FallIsLife.Data;
using UnityEngine;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>
    /// Route Planning (GDD §7): chart with dotted flight lines plus a carousel of postcard route cards.
    /// Left/Right cycles, Confirm stamps "APPROVED" and takes off.
    /// </summary>
    public class RoutePlanningScreen : UIScreen
    {
        private const string TitleName = "header-title";
        private const string SubtitleName = "header-subtitle";
        private const string FlockStatusName = "flock-status";
        private const string MapContainerName = "route-map-container";
        private const string CarouselName = "card-carousel";
        private const string PreviousButtonName = "prev-button";
        private const string NextButtonName = "next-button";
        private const string ConfirmButtonName = "confirm-button";
        private const float MillisecondsPerSecond = 1000f;
        private const int MaxObstacleNamesPerCard = 3;

        [Tooltip("Seconds the APPROVED stamp shows before taking off.")]
        [SerializeField] private float stampDelay = 0.7f;
        [Tooltip("Obstacle definitions used to list the top obstacle types on each card.")]
        [SerializeField] private List<ObstacleDefinition> obstacleDefinitions = new List<ObstacleDefinition>();

        private readonly List<RouteCardElement> cards = new List<RouteCardElement>();
        private RouteMapView mapView;
        private int selectedIndex;
        private bool isConfirming;

        /// <inheritdoc />
        protected override void BindScreen(VisualElement root)
        {
            GameFlowManager flowManager = GameFlowManager.Instance;
            RunState run = flowManager != null ? flowManager.RunState : null;
            RouteMapData routeMap = flowManager != null ? flowManager.RouteMap : null;
            if (run == null || run.CurrentStop == null || routeMap == null)
            {
                Debug.LogWarning("[RoutePlanningScreen] No RunState or route map available.");
                return;
            }

            List<RestStopData> options = run.CurrentStop.nextStops.Where(stop => stop != null).ToList();

            root.Q<Label>(TitleName).text = $"Night at {run.CurrentStop.displayName}";
            root.Q<Label>(SubtitleName).text = $"Day {run.DayIndex} of {run.TotalLegs}: choose tomorrow's lake";
            root.Q<Label>(FlockStatusName).text =
                $"GEESE x {run.FlockSize}   FOOD {Mathf.RoundToInt(run.Food)}   WATER {Mathf.RoundToInt(run.Water)}";

            VisualElement mapContainer = root.Q<VisualElement>(MapContainerName);
            mapContainer.Clear();
            mapView = new RouteMapView();
            mapContainer.Add(mapView);
            mapView.SetData(routeMap, run.CurrentStop, options, run.VisitedStops);

            VisualElement carousel = root.Q<VisualElement>(CarouselName);
            carousel.Clear();
            cards.Clear();
            float maxDistance = routeMap.MaxLegDistance;
            for (int i = 0; i < options.Count; i++)
            {
                var card = new RouteCardElement(options[i], maxDistance, GetTopObstacleNames(options[i].leg));
                int cardIndex = i;
                card.RegisterCallback<ClickEvent>(_ => Select(cardIndex));
                carousel.Add(card);
                cards.Add(card);
            }

            BindButton(root, PreviousButtonName, () => Step(-1));
            BindButton(root, NextButtonName, () => Step(1));
            BindButton(root, ConfirmButtonName, Confirm);

            isConfirming = false;
            Select(0);
        }

        /// <inheritdoc />
        protected override void OnNavigate(Vector2 direction)
        {
            if (Mathf.Abs(direction.x) >= Mathf.Abs(direction.y))
            {
                Step(direction.x > 0f ? 1 : -1);
            }
        }

        /// <inheritdoc />
        protected override void OnSubmit()
        {
            Confirm();
        }

        private void Step(int delta)
        {
            if (cards.Count == 0 || isConfirming)
            {
                return;
            }
            Select((selectedIndex + delta + cards.Count) % cards.Count);
        }

        private void Select(int index)
        {
            if (cards.Count == 0)
            {
                return;
            }
            selectedIndex = Mathf.Clamp(index, 0, cards.Count - 1);
            for (int i = 0; i < cards.Count; i++)
            {
                cards[i].SetSelected(i == selectedIndex);
            }
            mapView?.SetSelected(cards[selectedIndex].Stop);
        }

        private void Confirm()
        {
            if (cards.Count == 0 || isConfirming || GameFlowManager.Instance == null)
            {
                return;
            }
            isConfirming = true;
            AcceptsInput = false;
            RouteCardElement card = cards[selectedIndex];
            card.ShowStamp();
            Root.schedule.Execute(() => GameFlowManager.Instance.ConfirmRoute(card.Stop))
                .ExecuteLater((long)(stampDelay * MillisecondsPerSecond));
        }

        /// <summary>Top obstacle types: categories boosted by traits first, then eligible definitions by weight.</summary>
        private List<string> GetTopObstacleNames(LegSettings leg)
        {
            int hazard = leg.EffectiveHazardLevel;
            return obstacleDefinitions
                .Where(definition => definition != null &&
                                     (definition.minHazardLevel <= hazard || leg.GetObstacleMultiplier(definition.category) > 1f))
                .OrderByDescending(definition => definition.weight * leg.GetObstacleMultiplier(definition.category))
                .Select(definition => definition.category.ToString())
                .Distinct()
                .Take(MaxObstacleNamesPerCard)
                .ToList();
        }
    }
}
