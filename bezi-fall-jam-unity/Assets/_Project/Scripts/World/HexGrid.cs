using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>
    /// Flat-top hex math in "odd-q" offset coordinates: column spacing 1.5R along X, row spacing √3R along Z,
    /// odd columns shifted half a row forward. Tile centers sit at Y = 0.
    /// </summary>
    public readonly struct HexGrid
    {
        private const float SqrtThree = 1.7320508f;
        private const float ColumnSpacingFactor = 1.5f;
        private const float HalfRow = 0.5f;
        private const int OffsetDivisor = 2;

        public float Radius { get; }
        public float ColumnSpacing => ColumnSpacingFactor * Radius;
        public float RowSpacing => SqrtThree * Radius;

        /// <summary>Creates a grid for hexes with the given outer radius (center to corner).</summary>
        public HexGrid(float radius)
        {
            Radius = radius;
        }

        /// <summary>Returns true when a column is odd (works for negative columns).</summary>
        public static bool IsOddColumn(int column) => (column & 1) == 1;

        /// <summary>Converts offset (column, row) to a local-space tile center.</summary>
        public Vector3 OffsetToWorld(int column, int row)
        {
            float x = column * ColumnSpacing;
            float z = row * RowSpacing + (IsOddColumn(column) ? RowSpacing * HalfRow : 0f);
            return new Vector3(x, 0f, z);
        }

        /// <summary>Converts axial (q, r) to a local-space tile center.</summary>
        public Vector3 AxialToWorld(int q, int r)
        {
            float x = q * ColumnSpacing;
            float z = RowSpacing * (r + q * HalfRow);
            return new Vector3(x, 0f, z);
        }

        /// <summary>Converts axial (q, r) to odd-q offset (column, row).</summary>
        public static Vector2Int AxialToOffset(int q, int r)
        {
            int row = r + (q - (q & 1)) / OffsetDivisor;
            return new Vector2Int(q, row);
        }

        /// <summary>Converts odd-q offset (column, row) to axial (q, r).</summary>
        public static Vector2Int OffsetToAxial(int column, int row)
        {
            int r = row - (column - (column & 1)) / OffsetDivisor;
            return new Vector2Int(column, r);
        }

        /// <summary>Returns the row index containing a local Z position (ignores odd-column offset).</summary>
        public int WorldZToRow(float z) => Mathf.FloorToInt(z / RowSpacing);
    }
}
