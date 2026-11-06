using FallIsLife.Data;
using UnityEngine;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>Shared display conversions and small element builders for the flight-tracker style UI.</summary>
    public static class UIFormat
    {
        /// <summary>Flavor conversion from GDD §11: meters x 25 -> "ft".</summary>
        public const float FeetPerMeterDisplay = 25f;
        public const float MphPerMetersPerSecond = 2.23694f;
        public const float MetersPerKilometer = 1000f;
        public const float SecondsPerMinute = 60f;
        public const float PercentScale = 100f;
        public const float WindSpeedPerPip = 2f;
        public const int MaxWindPips = 2;
        public const string PipClass = "pip";
        public const string PipFilledClass = "pip--filled";

        /// <summary>Altitude display string, e.g. "ALT 650 ft".</summary>
        public static string Altitude(float meters) => $"ALT {Mathf.RoundToInt(meters * FeetPerMeterDisplay)} ft";

        /// <summary>Ground speed display string, e.g. "GS 31 mph".</summary>
        public static string GroundSpeed(float metersPerSecond) => $"GS {Mathf.RoundToInt(metersPerSecond * MphPerMetersPerSecond)} mph";

        /// <summary>Formats seconds as m:ss.</summary>
        public static string Duration(float seconds)
        {
            int total = Mathf.Max(0, Mathf.CeilToInt(seconds));
            int minutes = total / (int)SecondsPerMinute;
            int remainder = total % (int)SecondsPerMinute;
            return $"{minutes}:{remainder:00}";
        }

        /// <summary>Formats meters as kilometers, e.g. "1.4 km".</summary>
        public static string Kilometers(float meters) => $"{meters / MetersPerKilometer:0.0} km";

        /// <summary>Wind label: Tailwind / Calm / Headwind.</summary>
        public static string WindLabel(float windSpeed)
        {
            if (windSpeed > 0f)
            {
                return "Tailwind";
            }
            return windSpeed < 0f ? "Headwind" : "Calm";
        }

        /// <summary>ASCII arrow for wind direction relative to flight (south is "down" on the chart).</summary>
        public static string WindArrow(float windSpeed)
        {
            if (windSpeed > 0f)
            {
                return "v";
            }
            return windSpeed < 0f ? "^" : "-";
        }

        /// <summary>Wind strength in pips (0-2), 1 pip per WindSpeedPerPip m/s.</summary>
        public static int WindPips(float windSpeed) => Mathf.Clamp(Mathf.RoundToInt(Mathf.Abs(windSpeed) / WindSpeedPerPip), 0, MaxWindPips);

        /// <summary>Weather label.</summary>
        public static string Weather(WeatherType weather) => weather.ToString();

        /// <summary>Builds a row of pip elements with <paramref name="filled"/> of <paramref name="total"/> filled.</summary>
        public static VisualElement BuildPips(int filled, int total)
        {
            var row = new VisualElement();
            row.AddToClassList("pip-row");
            for (int i = 0; i < total; i++)
            {
                var pip = new VisualElement();
                pip.AddToClassList(PipClass);
                if (i < filled)
                {
                    pip.AddToClassList(PipFilledClass);
                }
                row.Add(pip);
            }
            return row;
        }

        /// <summary>Sets a fill element's width as a percentage (0-1).</summary>
        public static void SetFill(VisualElement fill, float normalized)
        {
            if (fill != null)
            {
                fill.style.width = Length.Percent(Mathf.Clamp01(normalized) * PercentScale);
            }
        }

        /// <summary>Fills a container with goose icons: <paramref name="present"/> solid, then <paramref name="faded"/> faded.</summary>
        public static void FillGooseIcons(VisualElement container, int present, int faded)
        {
            if (container == null)
            {
                return;
            }
            container.Clear();
            for (int i = 0; i < present + faded; i++)
            {
                var icon = new VisualElement();
                icon.AddToClassList("goose-icon");
                icon.EnableInClassList("goose-icon--lost", i >= present);
                container.Add(icon);
            }
        }

        /// <summary>Creates a label with USS classes.</summary>
        public static Label Label(string text, params string[] classes)
        {
            var label = new Label(text);
            foreach (string ussClass in classes)
            {
                label.AddToClassList(ussClass);
            }
            return label;
        }
    }
}
