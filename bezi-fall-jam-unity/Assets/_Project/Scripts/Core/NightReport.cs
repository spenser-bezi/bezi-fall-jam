using System;
using System.Collections.Generic;

namespace FallIsLife.Core
{
    /// <summary>What happened overnight at a lake. Shown by the Night Summary screen.</summary>
    [Serializable]
    public class NightReport
    {
        public int dayCompleted;
        public string lakeName;
        public int geeseStartedLeg;
        public int geeseArrived;
        public int geeseRecruited;
        public float foodBefore;
        public float foodAfter;
        public float waterBefore;
        public float waterAfter;
        public List<string> traitMessages = new List<string>();
    }
}
