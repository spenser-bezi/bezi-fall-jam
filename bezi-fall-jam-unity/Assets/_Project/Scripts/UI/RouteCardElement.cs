using System.Collections.Generic;
using FallIsLife.Data;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>
    /// Postcard-style route card showing every GDD §7 field from RestStopData: name + illustration, distance,
    /// wind, weather, hazards (+ top obstacle types), snacks, lake food/water, and traits.
    /// </summary>
    public class RouteCardElement : VisualElement
    {
        private const string CardClass = "route-card";
        private const string SelectedClass = "route-card--selected";
        private const string StampedClass = "route-card--stamped";
        private const string NoCapacityText = "-";
        private const string StampText = "APPROVED";

        private readonly Label stampLabel;

        /// <summary>The stop this card represents.</summary>
        public RestStopData Stop { get; }

        /// <summary>Builds a card for a stop. <paramref name="maxDistance"/> scales the leg-length bar.</summary>
        public RouteCardElement(RestStopData stop, float maxDistance, IReadOnlyList<string> topObstacleNames)
        {
            Stop = stop;
            AddToClassList(CardClass);
            LegSettings leg = stop.leg;

            var postcard = new VisualElement();
            postcard.AddToClassList("route-card__postcard");
            if (stop.postcard != null)
            {
                postcard.style.backgroundImage = new StyleBackground(stop.postcard);
            }
            postcard.Add(UIFormat.Label(stop.displayName, "route-card__title"));
            postcard.Add(UIFormat.Label(stop.subtitle, "route-card__subtitle"));
            Add(postcard);

            var stats = new VisualElement();
            stats.AddToClassList("route-card__stats");
            Add(stats);

            VisualElement distanceRow = AddRow(stats, "Distance", UIFormat.Kilometers(leg.distanceMeters));
            var bar = new VisualElement();
            bar.AddToClassList("bar");
            bar.AddToClassList("route-card__distance-bar");
            var fill = new VisualElement();
            fill.AddToClassList("bar__fill");
            bar.Add(fill);
            UIFormat.SetFill(fill, maxDistance > 0f ? leg.distanceMeters / maxDistance : 0f);
            distanceRow.Add(bar);

            string windText = $"{UIFormat.WindArrow(leg.windSpeed)} {UIFormat.WindLabel(leg.windSpeed)}";
            if (leg.JetStreamBonus > 0f)
            {
                windText += " + Jet Stream (High)";
            }
            VisualElement windRow = AddRow(stats, "Wind", windText);
            windRow.Add(UIFormat.BuildPips(UIFormat.WindPips(leg.windSpeed), UIFormat.MaxWindPips));

            AddRow(stats, "Weather", UIFormat.Weather(leg.weather));

            VisualElement hazardRow = AddRow(stats, "Hazards", string.Empty);
            hazardRow.Add(UIFormat.BuildPips(leg.EffectiveHazardLevel, LegSettings.MaxRating));
            if (topObstacleNames != null && topObstacleNames.Count > 0)
            {
                stats.Add(UIFormat.Label(string.Join(", ", topObstacleNames), "route-card__obstacles"));
            }

            VisualElement snackRow = AddRow(stats, "Snacks en route", string.Empty);
            snackRow.Add(UIFormat.BuildPips(leg.snackDensity, LegSettings.MaxRating));

            AddRow(stats, "Lake food", stop.foodCapacity > 0 ? $"Feeds ~{stop.foodCapacity}" : NoCapacityText);
            AddRow(stats, "Lake water", stop.waterCapacity > 0 ? $"Waters ~{stop.waterCapacity}" : NoCapacityText);

            var traits = new VisualElement();
            traits.AddToClassList("route-card__traits");
            foreach (RouteTraitData trait in leg.traits)
            {
                if (trait == null)
                {
                    continue;
                }
                Label traitName = UIFormat.Label(trait.displayName, "route-card__trait");
                traitName.tooltip = trait.description;
                traits.Add(traitName);
                traits.Add(UIFormat.Label(trait.description, "route-card__trait-description"));
            }
            Add(traits);

            stampLabel = UIFormat.Label(StampText, "route-card__stamp");
            Add(stampLabel);
        }

        /// <summary>Toggles the selected (front of carousel) look.</summary>
        public void SetSelected(bool isSelected)
        {
            EnableInClassList(SelectedClass, isSelected);
        }

        /// <summary>Shows the "APPROVED" stamp.</summary>
        public void ShowStamp()
        {
            AddToClassList(StampedClass);
        }

        private static VisualElement AddRow(VisualElement parent, string label, string value)
        {
            var row = new VisualElement();
            row.AddToClassList("route-card__row");
            row.Add(UIFormat.Label(label, "route-card__label"));
            if (!string.IsNullOrEmpty(value))
            {
                row.Add(UIFormat.Label(value, "route-card__value"));
            }
            parent.Add(row);
            return row;
        }
    }
}
