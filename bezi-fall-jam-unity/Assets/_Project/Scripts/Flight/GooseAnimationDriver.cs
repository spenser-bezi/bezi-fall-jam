using System.Collections.Generic;
using UnityEngine;

namespace FallIsLife.Flight
{
    /// <summary>
    /// Pushes the Animator parameter contract (Foundation plan section 4) to any Animator in children.
    /// Silently does nothing while the greybox visual has no Animator or the parameter is missing.
    /// </summary>
    public class GooseAnimationDriver : MonoBehaviour
    {
        public const string FlapSpeedParameter = "FlapSpeed";
        public const string BankParameter = "Bank";
        public const string HonkParameter = "Honk";
        public const string TumbleParameter = "Tumble";
        public const string IsSwimmingParameter = "IsSwimming";

        public const float MinFlapSpeed = 0f;
        public const float MaxFlapSpeed = 2f;
        public const float MinBank = -1f;
        public const float MaxBank = 1f;

        private static readonly int FlapSpeedHash = Animator.StringToHash(FlapSpeedParameter);
        private static readonly int BankHash = Animator.StringToHash(BankParameter);
        private static readonly int HonkHash = Animator.StringToHash(HonkParameter);
        private static readonly int TumbleHash = Animator.StringToHash(TumbleParameter);
        private static readonly int IsSwimmingHash = Animator.StringToHash(IsSwimmingParameter);

        [Tooltip("Set swimming on start (e.g. geese floating in the Night diorama).")]
        [SerializeField] private bool swimOnStart;

        private Animator animator;
        private readonly HashSet<int> availableParameters = new HashSet<int>();

        private void Awake()
        {
            RefreshAnimator();
        }

        private void Start()
        {
            if (swimOnStart)
            {
                SetSwimming(true);
            }
        }

        /// <summary>Re-finds the Animator in children (call after swapping the visual at runtime).</summary>
        public void RefreshAnimator()
        {
            animator = GetComponentInChildren<Animator>();
            availableParameters.Clear();
            if (animator == null || animator.runtimeAnimatorController == null)
            {
                return;
            }
            foreach (AnimatorControllerParameter parameter in animator.parameters)
            {
                availableParameters.Add(parameter.nameHash);
            }
        }

        /// <summary>Sets wing flap speed (0-2, 1 = normal cruise).</summary>
        public void SetFlapSpeed(float flapSpeed)
        {
            if (CanDrive(FlapSpeedHash))
            {
                animator.SetFloat(FlapSpeedHash, Mathf.Clamp(flapSpeed, MinFlapSpeed, MaxFlapSpeed));
            }
        }

        /// <summary>Sets bank (-1 = full left, 1 = full right).</summary>
        public void SetBank(float bank)
        {
            if (CanDrive(BankHash))
            {
                animator.SetFloat(BankHash, Mathf.Clamp(bank, MinBank, MaxBank));
            }
        }

        /// <summary>Fires the Honk trigger.</summary>
        public void TriggerHonk()
        {
            if (CanDrive(HonkHash))
            {
                animator.SetTrigger(HonkHash);
            }
        }

        /// <summary>Fires the Tumble trigger (collision).</summary>
        public void TriggerTumble()
        {
            if (CanDrive(TumbleHash))
            {
                animator.SetTrigger(TumbleHash);
            }
        }

        /// <summary>Sets the IsSwimming bool (Night diorama).</summary>
        public void SetSwimming(bool isSwimming)
        {
            if (CanDrive(IsSwimmingHash))
            {
                animator.SetBool(IsSwimmingHash, isSwimming);
            }
        }

        private bool CanDrive(int parameterHash)
        {
            return animator != null && animator.isActiveAndEnabled && availableParameters.Contains(parameterHash);
        }
    }
}
