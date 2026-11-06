using System.Collections.Generic;
using FallIsLife.Data;
using UnityEngine;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>
    /// 2D aeronautical-chart view of the route map: nodes per row and dotted flight lines generated from
    /// RouteMapData. Highlights today's options and draws the route taken so far.
    /// </summary>
    [UxmlElement]
    public partial class RouteMapView : VisualElement
    {
        private const string RootClass = "route-map";
        private const string NodeClass = "route-map__node";
        private const string NodeDotClass = "route-map__dot";
        private const string NodeLabelClass = "route-map__label";
        private const string NodeCurrentClass = "route-map__node--current";
        private const string NodeOptionClass = "route-map__node--option";
        private const string NodeVisitedClass = "route-map__node--visited";
        private const string NodeSelectedClass = "route-map__node--selected";

        private const float VerticalPadding = 0.1f;
        private const float DashLength = 8f;
        private const float GapLength = 6f;
        private const float FaintLineWidth = 1.5f;
        private const float OptionLineWidth = 2.5f;
        private const float SelectedLineWidth = 4f;
        private const float VisitedLineWidth = 3.5f;

        private static readonly Color FaintLineColor = new Color(0.35f, 0.25f, 0.2f, 0.35f);
        private static readonly Color OptionLineColor = new Color(0.878f, 0.478f, 0.184f, 0.8f);
        private static readonly Color SelectedLineColor = new Color(0.722f, 0.227f, 0.165f, 1f);
        private static readonly Color VisitedLineColor = new Color(0.169f, 0.184f, 0.353f, 0.9f);

        private readonly Dictionary<RestStopData, VisualElement> nodes = new Dictionary<RestStopData, VisualElement>();
        private readonly List<RestStopData> options = new List<RestStopData>();
        private readonly List<RestStopData> visited = new List<RestStopData>();
        private RouteMapData map;
        private RestStopData current;
        private RestStopData selected;

        /// <summary>Creates an empty chart; call <see cref="SetData"/> to populate it.</summary>
        public RouteMapView()
        {
            AddToClassList(RootClass);
            generateVisualContent += DrawLines;
            RegisterCallback<GeometryChangedEvent>(_ => LayoutNodes());
        }

        /// <summary>Rebuilds the chart for a route map, current stop, today's options, and visited path.</summary>
        public void SetData(RouteMapData routeMap, RestStopData currentStop, IEnumerable<RestStopData> todaysOptions, IEnumerable<RestStopData> visitedStops)
        {
            map = routeMap;
            current = currentStop;
            options.Clear();
            if (todaysOptions != null)
            {
                options.AddRange(todaysOptions);
            }
            visited.Clear();
            if (visitedStops != null)
            {
                visited.AddRange(visitedStops);
            }
            BuildNodes();
            LayoutNodes();
            MarkDirtyRepaint();
        }

        /// <summary>Highlights the currently selected option (thicker line, accent node).</summary>
        public void SetSelected(RestStopData stop)
        {
            selected = stop;
            foreach (KeyValuePair<RestStopData, VisualElement> pair in nodes)
            {
                pair.Value.EnableInClassList(NodeSelectedClass, pair.Key == selected);
            }
            MarkDirtyRepaint();
        }

        private void BuildNodes()
        {
            foreach (VisualElement node in nodes.Values)
            {
                node.RemoveFromHierarchy();
            }
            nodes.Clear();
            if (map == null)
            {
                return;
            }

            foreach (RestStopData stop in map.allStops)
            {
                if (stop == null)
                {
                    continue;
                }
                var node = new VisualElement();
                node.AddToClassList(NodeClass);
                node.EnableInClassList(NodeCurrentClass, stop == current);
                node.EnableInClassList(NodeOptionClass, options.Contains(stop));
                node.EnableInClassList(NodeVisitedClass, visited.Contains(stop));
                node.EnableInClassList(NodeSelectedClass, stop == selected);
                node.pickingMode = PickingMode.Ignore;

                var dot = new VisualElement();
                dot.AddToClassList(NodeDotClass);
                node.Add(dot);
                node.Add(UIFormat.Label(stop.displayName, NodeLabelClass));

                Add(node);
                nodes[stop] = node;
            }
        }

        private void LayoutNodes()
        {
            Rect rect = contentRect;
            if (map == null || float.IsNaN(rect.width) || rect.width <= 0f)
            {
                return;
            }
            foreach (KeyValuePair<RestStopData, VisualElement> pair in nodes)
            {
                Vector2 position = GetLocalPosition(pair.Key, rect);
                pair.Value.style.position = Position.Absolute;
                pair.Value.style.left = position.x;
                pair.Value.style.top = position.y;
            }
            MarkDirtyRepaint();
        }

        private Vector2 GetLocalPosition(RestStopData stop, Rect rect)
        {
            int maxRow = Mathf.Max(1, map.MaxRow);
            float y = Mathf.Lerp(VerticalPadding, 1f - VerticalPadding, (float)stop.row / maxRow);

            List<RestStopData> rowStops = map.GetStopsInRow(stop.row);
            int index = Mathf.Max(0, rowStops.IndexOf(stop));
            float x = (index + 1f) / (rowStops.Count + 1f);
            return new Vector2(x * rect.width, y * rect.height);
        }

        private void DrawLines(MeshGenerationContext context)
        {
            Rect rect = contentRect;
            if (map == null || rect.width <= 0f)
            {
                return;
            }

            Painter2D painter = context.painter2D;
            foreach (RestStopData stop in map.allStops)
            {
                if (stop == null)
                {
                    continue;
                }
                Vector2 from = GetLocalPosition(stop, rect);
                foreach (RestStopData next in stop.nextStops)
                {
                    if (next == null)
                    {
                        continue;
                    }
                    Vector2 to = GetLocalPosition(next, rect);
                    if (IsVisitedEdge(stop, next))
                    {
                        DrawSolid(painter, from, to, VisitedLineColor, VisitedLineWidth);
                    }
                    else if (stop == current && options.Contains(next))
                    {
                        bool isSelected = next == selected;
                        DrawDashed(painter, from, to, isSelected ? SelectedLineColor : OptionLineColor, isSelected ? SelectedLineWidth : OptionLineWidth);
                    }
                    else
                    {
                        DrawDashed(painter, from, to, FaintLineColor, FaintLineWidth);
                    }
                }
            }
        }

        private bool IsVisitedEdge(RestStopData from, RestStopData to)
        {
            for (int i = 0; i < visited.Count - 1; i++)
            {
                if (visited[i] == from && visited[i + 1] == to)
                {
                    return true;
                }
            }
            return false;
        }

        private static void DrawSolid(Painter2D painter, Vector2 from, Vector2 to, Color color, float width)
        {
            painter.strokeColor = color;
            painter.lineWidth = width;
            painter.BeginPath();
            painter.MoveTo(from);
            painter.LineTo(to);
            painter.Stroke();
        }

        private static void DrawDashed(Painter2D painter, Vector2 from, Vector2 to, Color color, float width)
        {
            float length = Vector2.Distance(from, to);
            if (length <= 0f)
            {
                return;
            }
            Vector2 direction = (to - from) / length;
            painter.strokeColor = color;
            painter.lineWidth = width;
            painter.BeginPath();
            for (float distance = 0f; distance < length; distance += DashLength + GapLength)
            {
                float dashEnd = Mathf.Min(distance + DashLength, length);
                painter.MoveTo(from + direction * distance);
                painter.LineTo(from + direction * dashEnd);
            }
            painter.Stroke();
        }
    }
}
