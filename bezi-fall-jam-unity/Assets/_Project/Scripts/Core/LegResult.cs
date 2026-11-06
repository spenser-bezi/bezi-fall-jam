using System;

namespace FallIsLife.Core
{
    /// <summary>Outcome of one flight leg, produced by the Flight phase and stored in RunState.History.</summary>
    [Serializable]
    public struct LegResult
    {
        public string destinationName;
        public int geeseAtStart;
        public int geeseAtEnd;
        public int lostToCollision;
        public int lostToHunger;
        public int lostToThirst;
        public int lostToStraggling;
        public int recruits;
        public float foodAtEnd;
        public float waterAtEnd;
        public int snacksEaten;

        /// <summary>True when at least one goose (the leader) reached the destination.</summary>
        public bool Arrived => geeseAtEnd > 0;

        /// <summary>Total geese lost on this leg across all reasons.</summary>
        public int TotalLost => lostToCollision + lostToHunger + lostToThirst + lostToStraggling;

        /// <summary>Returns the number of geese lost for a specific reason.</summary>
        public int GetLost(GooseLossReason reason)
        {
            switch (reason)
            {
                case GooseLossReason.Collision: return lostToCollision;
                case GooseLossReason.Hunger: return lostToHunger;
                case GooseLossReason.Thirst: return lostToThirst;
                case GooseLossReason.Straggled: return lostToStraggling;
                default: return 0;
            }
        }

        /// <summary>Sets the number of geese lost for a specific reason.</summary>
        public void SetLost(GooseLossReason reason, int count)
        {
            switch (reason)
            {
                case GooseLossReason.Collision: lostToCollision = count; break;
                case GooseLossReason.Hunger: lostToHunger = count; break;
                case GooseLossReason.Thirst: lostToThirst = count; break;
                case GooseLossReason.Straggled: lostToStraggling = count; break;
            }
        }
    }
}
