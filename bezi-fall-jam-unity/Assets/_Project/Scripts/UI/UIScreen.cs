using FallIsLife.Input;
using UnityEngine;
using UnityEngine.UIElements;

namespace FallIsLife.UI
{
    /// <summary>
    /// Base for UI Toolkit screens. Owns the UIDocument root and a UI-map controls instance, and turns
    /// Navigate/Submit/Cancel into simple virtual callbacks (one step per stick/arrow press).
    /// Buttons should be non-focusable so Submit is handled only here.
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public abstract class UIScreen : MonoBehaviour
    {
        private const float NavigateThreshold = 0.5f;

        private FallIsLifeControls controls;
        private bool navigateIsNeutral = true;

        protected UIDocument Document { get; private set; }
        protected VisualElement Root { get; private set; }

        /// <summary>When false, Navigate/Submit/Cancel callbacks are not invoked.</summary>
        protected bool AcceptsInput { get; set; } = true;

        protected virtual void OnEnable()
        {
            Document = GetComponent<UIDocument>();
            Root = Document.rootVisualElement;
            controls = new FallIsLifeControls();
            controls.UI.Enable();
            controls.UI.Submit.performed += HandleSubmit;
            controls.UI.Cancel.performed += HandleCancel;
            BindScreen(Root);
        }

        protected virtual void OnDisable()
        {
            if (controls != null)
            {
                controls.UI.Submit.performed -= HandleSubmit;
                controls.UI.Cancel.performed -= HandleCancel;
                controls.Dispose();
                controls = null;
            }
        }

        protected virtual void Update()
        {
            if (controls == null)
            {
                return;
            }
            Vector2 navigate = controls.UI.Navigate.ReadValue<Vector2>();
            bool isNeutral = navigate.magnitude < NavigateThreshold;
            if (navigateIsNeutral && !isNeutral && AcceptsInput)
            {
                OnNavigate(navigate);
            }
            navigateIsNeutral = isNeutral;
        }

        /// <summary>Queries elements and binds callbacks. Called every time the screen is enabled.</summary>
        protected abstract void BindScreen(VisualElement root);

        /// <summary>Called once per Navigate press with the raw direction.</summary>
        protected virtual void OnNavigate(Vector2 direction)
        {
        }

        /// <summary>Called on Submit (Enter / gamepad South).</summary>
        protected virtual void OnSubmit()
        {
        }

        /// <summary>Called on Cancel (Esc / gamepad East).</summary>
        protected virtual void OnCancel()
        {
        }

        /// <summary>Finds a button by name, makes it non-focusable, and binds its click.</summary>
        protected Button BindButton(VisualElement root, string buttonName, System.Action onClick)
        {
            Button button = root.Q<Button>(buttonName);
            if (button == null)
            {
                Debug.LogWarning($"[{GetType().Name}] Button '{buttonName}' not found in UXML.");
                return null;
            }
            button.focusable = false;
            button.clicked += onClick;
            return button;
        }

        private void HandleSubmit(UnityEngine.InputSystem.InputAction.CallbackContext context)
        {
            if (AcceptsInput)
            {
                OnSubmit();
            }
        }

        private void HandleCancel(UnityEngine.InputSystem.InputAction.CallbackContext context)
        {
            if (AcceptsInput)
            {
                OnCancel();
            }
        }
    }
}
