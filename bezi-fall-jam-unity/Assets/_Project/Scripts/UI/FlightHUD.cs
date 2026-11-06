using System.Collections.Generic;
using FallIsLife.Core;
using FallIsLife.Flight;
using UnityEngine;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>
    /// "Flight tracker for the flock" HUD (GDD §11): flight code, day, route, altitude, ground speed, ETA,
    /// progress, traffic warning, flock count, Food/Water, wind, and world-space straggler markers.
    /// </summary>
    public class FlightHUD : UIScreen
    {
        private const string FlightCodeName = "flight-code";
        private const string RouteLabelName = "route-label";
        private const string AltitudeName = "altitude-label";
        private const string BandName = "band-label";
        private const string SpeedName = "speed-label";
        private const string EtaName = "eta-label";
        private const string ProgressFillName = "progress-fill";
        private const string TrafficWarningName = "traffic-warning";
        private const string GeeseLabelName = "geese-label";
        private const string GeeseIconsName = "geese-icons";
        private const string FoodFillName = "food-fill";
        private const string WaterFillName = "water-fill";
        private const string WindLabelName = "wind-label";
        private const string MarkerLayerName = "marker-layer";
        private const string HiddenClass = "hidden";
        private const string LowMeterClass = "bar__fill--low";
        private const string MarkerClass = "straggler-marker";
        private const string FlightCodeFormat = "FLIGHT HONK-{0:00}";
        private const float MarkerHeightOffset = 2.5f;

        [SerializeField] private float warningDisplayDuration = 2.5f;
        [Range(0f, 1f)]
        [SerializeField] private float lowMeterThreshold = 0.25f;

        private readonly List<Label> markerPool = new List<Label>();
        private Label flightCodeLabel;
        private Label routeLabel;
        private Label altitudeLabel;
        private Label bandLabel;
        private Label speedLabel;
        private Label etaLabel;
        private VisualElement progressFill;
        private Label trafficWarning;
        private Label geeseLabel;
        private VisualElement geeseIcons;
        private VisualElement foodFill;
        private VisualElement waterFill;
        private Label windLabel;
        private VisualElement markerLayer;
        private float warningTimeRemaining;
        private int displayedFlockSize = -1;
        private Camera worldCamera;

        /// <inheritdoc />
        protected override void BindScreen(VisualElement root)
        {
            flightCodeLabel = root.Q<Label>(FlightCodeName);
            routeLabel = root.Q<Label>(RouteLabelName);
            altitudeLabel = root.Q<Label>(AltitudeName);
            bandLabel = root.Q<Label>(BandName);
            speedLabel = root.Q<Label>(SpeedName);
            etaLabel = root.Q<Label>(EtaName);
            progressFill = root.Q<VisualElement>(ProgressFillName);
            trafficWarning = root.Q<Label>(TrafficWarningName);
            geeseLabel = root.Q<Label>(GeeseLabelName);
            geeseIcons = root.Q<VisualElement>(GeeseIconsName);
            foodFill = root.Q<VisualElement>(FoodFillName);
            waterFill = root.Q<VisualElement>(WaterFillName);
            windLabel = root.Q<Label>(WindLabelName);
            markerLayer = root.Q<VisualElement>(MarkerLayerName);
            trafficWarning?.AddToClassList(HiddenClass);

            GameEvents.FlockSizeChanged += HandleFlockSizeChanged;
            GameEvents.ResourceChanged += HandleResourceChanged;
            GameEvents.LegProgressChanged += HandleProgressChanged;
            GameEvents.HazardWarning += HandleHazardWarning;
        }

        /// <inheritdoc />
        protected override void OnDisable()
        {
            GameEvents.FlockSizeChanged -= HandleFlockSizeChanged;
            GameEvents.ResourceChanged -= HandleResourceChanged;
            GameEvents.LegProgressChanged -= HandleProgressChanged;
            GameEvents.HazardWarning -= HandleHazardWarning;
            base.OnDisable();
        }

        /// <inheritdoc />
        protected override void Update()
        {
            base.Update();
            FlightSceneController flight = FlightSceneController.Current;
            if (flight == null || !flight.IsReady || flight.Leader == null)
            {
                return;
            }

            RunState run = flight.RunState;
            flightCodeLabel.text = $"{string.Format(FlightCodeFormat, run.DayIndex)} . Day {run.DayIndex}/{run.TotalLegs}";
            string from = run.CurrentStop != null ? run.CurrentStop.displayName : string.Empty;
            string to = run.NextStop != null ? run.NextStop.displayName : string.Empty;
            routeLabel.text = $"{from} -> {to}";

            LeaderGooseController leader = flight.Leader;
            altitudeLabel.text = UIFormat.Altitude(leader.Altitude);
            bandLabel.text = leader.CurrentBand.ToString().ToUpperInvariant();
            speedLabel.text = UIFormat.GroundSpeed(leader.ForwardSpeed);
            etaLabel.text = $"ETA {UIFormat.Duration(flight.Progress.EtaSeconds)}";

            string wind = $"Wind {UIFormat.WindArrow(leader.LegWind)} {UIFormat.WindLabel(leader.LegWind)}";
            if (leader.IsInJetStream)
            {
                wind += " + Jet Stream";
            }
            if (flight.Resources.IsInStorm)
            {
                wind += "  [STORM]";
            }
            windLabel.text = wind;

            if (displayedFlockSize != flight.Flock.FlockSize)
            {
                HandleFlockSizeChanged(flight.Flock.FlockSize);
            }

            UpdateWarning();
            UpdateStragglerMarkers(flight.Flock);
        }

        private void HandleFlockSizeChanged(int newSize)
        {
            displayedFlockSize = newSize;
            if (geeseLabel != null)
            {
                geeseLabel.text = $"GEESE x {newSize}";
            }
            FlightSceneController flight = FlightSceneController.Current;
            int startSize = flight != null && flight.Flock != null ? flight.Flock.StartingSize : newSize;
            UIFormat.FillGooseIcons(geeseIcons, newSize, Mathf.Max(0, startSize - newSize));
        }

        private void HandleResourceChanged(ResourceType type, float normalizedValue)
        {
            VisualElement fill = type == ResourceType.Food ? foodFill : waterFill;
            UIFormat.SetFill(fill, normalizedValue);
            fill?.EnableInClassList(LowMeterClass, normalizedValue <= lowMeterThreshold);
        }

        private void HandleProgressChanged(float normalizedProgress)
        {
            UIFormat.SetFill(progressFill, normalizedProgress);
        }

        private void HandleHazardWarning(string label, Vector3 worldPosition)
        {
            if (trafficWarning == null)
            {
                return;
            }
            FlightSceneController flight = FlightSceneController.Current;
            float leaderX = flight != null && flight.Leader != null ? flight.Leader.transform.position.x : 0f;
            string arrow = worldPosition.x >= leaderX ? "->" : "<-";
            trafficWarning.text = worldPosition.x >= leaderX ? $"[!] {label} {arrow}" : $"{arrow} {label} [!]";
            trafficWarning.RemoveFromClassList(HiddenClass);
            warningTimeRemaining = warningDisplayDuration;
        }

        private void UpdateWarning()
        {
            if (warningTimeRemaining <= 0f)
            {
                return;
            }
            warningTimeRemaining -= Time.deltaTime;
            if (warningTimeRemaining <= 0f)
            {
                trafficWarning?.AddToClassList(HiddenClass);
            }
        }

        private void UpdateStragglerMarkers(FlockController flock)
        {
            if (markerLayer == null)
            {
                return;
            }
            if (worldCamera == null)
            {
                worldCamera = Camera.main;
            }

            int used = 0;
            if (worldCamera != null && Root.panel != null)
            {
                foreach (FollowerGoose follower in flock.Followers)
                {
                    if (follower == null || follower.State != GooseState.Straggling)
                    {
                        continue;
                    }
                    Vector3 worldPosition = follower.transform.position + Vector3.up * MarkerHeightOffset;
                    if (worldCamera.WorldToViewportPoint(worldPosition).z <= 0f)
                    {
                        continue;
                    }
                    Label marker = GetMarker(used++);
                    Vector2 panelPosition = RuntimePanelUtils.CameraTransformWorldToPanel(Root.panel, worldPosition, worldCamera);
                    marker.style.left = panelPosition.x;
                    marker.style.top = panelPosition.y;
                    marker.text = $"! {follower.StragglerTimeRemaining:0.0}";
                    marker.RemoveFromClassList(HiddenClass);
                }
            }

            for (int i = used; i < markerPool.Count; i++)
            {
                markerPool[i].AddToClassList(HiddenClass);
            }
        }

        private Label GetMarker(int index)
        {
            while (markerPool.Count <= index)
            {
                Label marker = UIFormat.Label(string.Empty, MarkerClass);
                marker.pickingMode = PickingMode.Ignore;
                markerLayer.Add(marker);
                markerPool.Add(marker);
            }
            return markerPool[index];
        }
    }
}
