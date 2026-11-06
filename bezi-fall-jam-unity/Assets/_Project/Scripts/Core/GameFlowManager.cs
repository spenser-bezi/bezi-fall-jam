using System.Collections;
using FallIsLife.Data;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace FallIsLife.Core
{
    /// <summary>
    /// Owns the RunState and RouteMapData and drives the phase loop:
    /// MainMenu -> RoutePlanning -> Flight -> Night -> ... -> Results.
    /// Lives on the DontDestroyOnLoad GameSystems prefab and loads one phase scene at a time (additive).
    /// </summary>
    public class GameFlowManager : MonoBehaviour
    {
        private const float NormalTimeScale = 1f;
        private const int DebugGeeseLost = 1;
        private const float DebugMeterFractionAtEnd = 0.5f;
        private const int DebugSnacksEaten = 3;

        [SerializeField] private RouteMapData routeMap;
        [SerializeField] private FlockBalance flockBalance;
        [SerializeField] private ResourceBalance resourceBalance;
        [Tooltip("Destination used by the debug RunState when a phase scene is played on its own.")]
        [SerializeField] private RestStopData debugNextStop;

        private Scene loadedPhaseScene;
        private bool isLoading;

        /// <summary>The single live instance (null until GameSystems exists).</summary>
        public static GameFlowManager Instance { get; private set; }

        public RunState RunState { get; private set; }
        public RouteMapData RouteMap => routeMap;
        public FlockBalance FlockBalance => flockBalance;
        public ResourceBalance ResourceBalance => resourceBalance;
        public GamePhase CurrentPhase { get; private set; }
        public bool IsLoading => isLoading;

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);

            Scene activeScene = SceneManager.GetActiveScene();
            if (SceneNames.TryGetPhase(activeScene.name, out GamePhase phase))
            {
                CurrentPhase = phase;
            }
            if (activeScene.name != SceneNames.Boot)
            {
                loadedPhaseScene = activeScene;
            }
            RunState = CreateDebugRunState(activeScene.name);
        }

        private void Start()
        {
            if (SceneManager.GetActiveScene().name == SceneNames.Boot)
            {
                ReturnToMainMenu();
            }
            else
            {
                GameEvents.RaisePhaseChanged(CurrentPhase);
            }
        }

        private void OnDestroy()
        {
            if (Instance == this)
            {
                Instance = null;
            }
        }

        /// <summary>Starts a brand-new run at the route's start stop and opens Route Planning.</summary>
        public void StartNewRun()
        {
            RunState = RunState.CreateNew(routeMap, flockBalance, resourceBalance);
            LoadPhase(GamePhase.RoutePlanning);
        }

        /// <summary>Sets tomorrow's destination and takes off into the Flight phase.</summary>
        public void ConfirmRoute(RestStopData destination)
        {
            if (destination == null)
            {
                Debug.LogWarning("[GameFlowManager] ConfirmRoute called without a destination.");
                return;
            }
            RunState.NextStop = destination;
            LoadPhase(GamePhase.Flight);
        }

        /// <summary>
        /// Called by the Flight phase when a leg ends. Applies the result, then goes to Night,
        /// or to Results on a win (destination reached) or loss (flock size 0).
        /// </summary>
        public void CompleteLeg(LegResult result)
        {
            RunState.ApplyLegResult(result);
            GameEvents.RaiseLegCompleted(result);

            if (!result.Arrived)
            {
                RunState.Outcome = RunOutcome.Lost;
                LoadPhase(GamePhase.Results);
                return;
            }

            if (RunState.NextStop != null)
            {
                RunState.CurrentStop = RunState.NextStop;
                RunState.VisitedStops.Add(RunState.CurrentStop);
            }
            RunState.NextStop = null;

            bool reachedDestination = routeMap != null && RunState.CurrentStop == routeMap.destinationStop;
            if (reachedDestination)
            {
                RunState.Outcome = RunOutcome.Won;
                LoadPhase(GamePhase.Results);
                return;
            }

            RunState.ApplyNightRest(RunState.CurrentStop, result, resourceBalance, flockBalance);
            RunState.DayIndex++;
            LoadPhase(GamePhase.Night);
        }

        /// <summary>Leaves the Night Summary and opens Route Planning for the next day.</summary>
        public void ContinueFromNight()
        {
            LoadPhase(GamePhase.RoutePlanning);
        }

        /// <summary>Returns to the Main Menu (from pause, results, or boot).</summary>
        public void ReturnToMainMenu()
        {
            LoadPhase(GamePhase.MainMenu);
        }

        private void LoadPhase(GamePhase phase)
        {
            if (isLoading)
            {
                return;
            }
            StartCoroutine(LoadPhaseRoutine(phase));
        }

        private IEnumerator LoadPhaseRoutine(GamePhase phase)
        {
            isLoading = true;
            Time.timeScale = NormalTimeScale;

            string sceneName = SceneNames.ForPhase(phase);
            Scene previousScene = loadedPhaseScene;
            bool hasPreviousScene = previousScene.IsValid() && previousScene.isLoaded;

            // Normal Boot flow: another scene (Boot) keeps the game alive, so unload the old phase
            // first and never show two phases at once. A phase played on its own is the only
            // loaded scene and cannot be unloaded first, so it is unloaded after the new one loads.
            bool unloadFirst = hasPreviousScene && SceneManager.sceneCount > 1;
            if (unloadFirst)
            {
                yield return SceneManager.UnloadSceneAsync(previousScene);
            }

            yield return SceneManager.LoadSceneAsync(sceneName, LoadSceneMode.Additive);

            Scene newScene = GetLastLoadedScene(sceneName);
            if (newScene.IsValid())
            {
                SceneManager.SetActiveScene(newScene);
                loadedPhaseScene = newScene;
            }

            if (!unloadFirst && hasPreviousScene && previousScene.isLoaded && previousScene != newScene)
            {
                yield return SceneManager.UnloadSceneAsync(previousScene);
            }

            CurrentPhase = phase;
            isLoading = false;
            GameEvents.RaisePhaseChanged(phase);
        }

        /// <summary>
        /// Returns the most recently loaded scene with the given name (handles the case where the
        /// same phase scene is briefly loaded twice, e.g. when a phase reloads itself).
        /// </summary>
        private static Scene GetLastLoadedScene(string sceneName)
        {
            for (int index = SceneManager.sceneCount - 1; index >= 0; index--)
            {
                Scene scene = SceneManager.GetSceneAt(index);
                if (scene.name == sceneName && scene.isLoaded)
                {
                    return scene;
                }
            }
            return default;
        }

        /// <summary>
        /// Builds a RunState so any phase scene can be played on its own: default flock,
        /// a default destination, and a synthetic previous leg for Night/Results.
        /// </summary>
        private RunState CreateDebugRunState(string activeSceneName)
        {
            RunState state = RunState.CreateNew(routeMap, flockBalance, resourceBalance);
            state.IsDebugRun = true;

            RestStopData start = routeMap != null ? routeMap.startStop : null;
            RestStopData destination = debugNextStop;
            if (destination == null && start != null && start.nextStops.Count > 0)
            {
                destination = start.nextStops[0];
            }
            state.NextStop = destination;

            bool needsHistory = activeSceneName == SceneNames.Night || activeSceneName == SceneNames.Results;
            if (needsHistory && destination != null)
            {
                var debugLeg = new LegResult
                {
                    destinationName = destination.displayName,
                    geeseAtStart = state.FlockSize,
                    geeseAtEnd = state.FlockSize - DebugGeeseLost,
                    lostToStraggling = DebugGeeseLost,
                    foodAtEnd = resourceBalance.startingFood * DebugMeterFractionAtEnd,
                    waterAtEnd = resourceBalance.startingWater * DebugMeterFractionAtEnd,
                    snacksEaten = DebugSnacksEaten
                };
                state.ApplyLegResult(debugLeg);
                state.CurrentStop = destination;
                state.VisitedStops.Add(destination);
                state.NextStop = null;
                state.ApplyNightRest(destination, debugLeg, resourceBalance, flockBalance);
                state.DayIndex++;
                state.Outcome = activeSceneName == SceneNames.Results ? RunOutcome.Won : RunOutcome.InProgress;
            }
            return state;
        }
    }
}
