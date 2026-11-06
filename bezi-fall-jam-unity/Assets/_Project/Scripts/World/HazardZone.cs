using System.Collections.Generic;
using FallIsLife.Flight;
using UnityEngine;

namespace FallIsLife.World
{
    /// <summary>
    /// Storm cloud zone on the HazardZone layer: doubles drain while the leader is inside and periodically
    /// telegraphs a lightning flash, then knocks a goose inside out of formation (GDD §5.8).
    /// </summary>
    public class HazardZone : Obstacle
    {
        [SerializeField] private Light lightningFlash;
        [SerializeField] private float strikeInterval = 3.5f;
        [SerializeField] private float telegraphDuration = 0.6f;
        [SerializeField] private float flashIntensity = 8f;
        [SerializeField] private float flickerFrequency = 30f;

        private readonly HashSet<GooseAgent> geeseInside = new HashSet<GooseAgent>();
        private readonly List<GooseAgent> strikeCandidates = new List<GooseAgent>();
        private FlockResources stormResources;
        private float strikeTimer;
        private float telegraphTimer;

        private void Start()
        {
            SetFlash(0f);
        }

        private void OnDisable()
        {
            if (stormResources != null)
            {
                stormResources.SetInStorm(false);
                stormResources = null;
            }
        }

        /// <summary>Tracks the goose; the leader entering turns on the storm drain multiplier.</summary>
        protected override void OnGooseEnter(GooseAgent goose)
        {
            geeseInside.Add(goose);
            if (goose.IsLeader && goose.Flock != null && goose.Flock.Resources != null && stormResources == null)
            {
                stormResources = goose.Flock.Resources;
                stormResources.SetInStorm(true);
            }
        }

        /// <summary>Stops tracking the goose; the leader leaving turns the storm drain off.</summary>
        protected override void OnGooseExit(GooseAgent goose)
        {
            geeseInside.Remove(goose);
            if (goose.IsLeader && stormResources != null)
            {
                stormResources.SetInStorm(false);
                stormResources = null;
            }
        }

        private void Update()
        {
            geeseInside.RemoveWhere(goose => goose == null);
            if (geeseInside.Count == 0)
            {
                strikeTimer = 0f;
                telegraphTimer = 0f;
                SetFlash(0f);
                return;
            }

            if (telegraphTimer > 0f)
            {
                telegraphTimer -= Time.deltaTime;
                float flicker = Mathf.Abs(Mathf.Sin(Time.time * flickerFrequency));
                SetFlash(flicker * flashIntensity);
                if (telegraphTimer <= 0f)
                {
                    Strike();
                    SetFlash(0f);
                }
                return;
            }

            strikeTimer += Time.deltaTime;
            if (strikeTimer >= strikeInterval)
            {
                strikeTimer = 0f;
                telegraphTimer = telegraphDuration;
            }
        }

        private void Strike()
        {
            strikeCandidates.Clear();
            foreach (GooseAgent goose in geeseInside)
            {
                if (goose != null && !goose.IsLeader && goose.IsActiveInFlock)
                {
                    strikeCandidates.Add(goose);
                }
            }
            if (strikeCandidates.Count > 0)
            {
                strikeCandidates[Random.Range(0, strikeCandidates.Count)].OnObstacleHit(this);
            }
        }

        private void SetFlash(float intensity)
        {
            if (lightningFlash != null)
            {
                lightningFlash.intensity = intensity;
                lightningFlash.enabled = intensity > 0f;
            }
        }
    }
}
