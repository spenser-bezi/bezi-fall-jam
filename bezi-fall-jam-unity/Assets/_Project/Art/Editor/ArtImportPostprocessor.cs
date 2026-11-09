using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace FallIsLife.EditorTools
{
    /// <summary>
    /// Applies the Art Workflow import rules (model, rig, animation loops, material remap and palette
    /// texture settings) to everything under Assets/_Project/Art.
    /// </summary>
    public class ArtImportPostprocessor : AssetPostprocessor
    {
        private const string ArtRoot = "Assets/_Project/Art/";
        private const string PaletteMaterialFolder = "Assets/_Project/Art/Materials/Palette/";
        private const string PaletteTextureName = "T_Palette_Fall";
        private const string GooseRigName = "SK_Goose";
        private const string GooseRootBoneName = "root";

        // Material slot names exported by Blender, remapped to project materials by name.
        private static readonly string[] RemappedMaterialNames = { "M_Palette_Fall", "M_Water", "M_Glow" };

        // FBXs that carry animation takes and need a Generic rig.
        private static readonly string[] AnimatedModelNameFragments = { "SK_", "WindFarm", "Windmill_Blades", "Plane_Prop" };

        // Clip name fragments that must not loop; every other clip loops.
        private static readonly string[] NonLoopingClipFragments = { "Honk", "Tumble" };

        private static bool IsArtModel(string path)
        {
            return path.StartsWith(ArtRoot, StringComparison.Ordinal)
                && path.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase);
        }

        private static bool IsAnimatedModel(string path)
        {
            string fileName = System.IO.Path.GetFileNameWithoutExtension(path);
            foreach (string fragment in AnimatedModelNameFragments)
            {
                if (fileName.Contains(fragment)) return true;
            }
            return false;
        }

        private static bool IsLoopingClip(string clipName)
        {
            foreach (string fragment in NonLoopingClipFragments)
            {
                if (clipName.Contains(fragment)) return false;
            }
            return true;
        }

        private void OnPreprocessModel()
        {
            if (!IsArtModel(assetPath)) return;

            var importer = (ModelImporter)assetImporter;
            importer.globalScale = 1f;
            importer.useFileScale = true;
            importer.bakeAxisConversion = true;
            importer.importCameras = false;
            importer.importLights = false;
            importer.importVisibility = false;
            importer.meshCompression = ModelImporterMeshCompression.Off;
            importer.isReadable = false;
            importer.addCollider = false;
            importer.importNormals = ModelImporterNormals.Import;
            importer.importTangents = ModelImporterTangents.CalculateMikk;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            importer.materialLocation = ModelImporterMaterialLocation.InPrefab;

            if (IsAnimatedModel(assetPath))
            {
                importer.importAnimation = true;
                importer.animationType = ModelImporterAnimationType.Generic;
                importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                if (System.IO.Path.GetFileNameWithoutExtension(assetPath).Contains(GooseRigName))
                {
                    importer.motionNodeName = GooseRootBoneName;
                }
            }
            else
            {
                importer.importAnimation = false;
                importer.animationType = ModelImporterAnimationType.None;
            }
        }

        private void OnPreprocessAnimation()
        {
            if (!IsArtModel(assetPath)) return;

            var importer = (ModelImporter)assetImporter;
            ModelImporterClipAnimation[] clips = importer.defaultClipAnimations;
            if (clips == null || clips.Length == 0) return;

            var result = new List<ModelImporterClipAnimation>(clips.Length);
            foreach (ModelImporterClipAnimation clip in clips)
            {
                bool loop = IsLoopingClip(clip.name);
                clip.loopTime = loop;
                clip.loop = loop;
                result.Add(clip);
            }
            importer.clipAnimations = result.ToArray();
        }

        // Replaces the FBX material slots with the shared project materials, so nothing is auto-extracted.
        private Material OnAssignMaterialModel(Material material, Renderer renderer)
        {
            if (!IsArtModel(assetPath)) return null;

            foreach (string materialName in RemappedMaterialNames)
            {
                if (!material.name.StartsWith(materialName, StringComparison.Ordinal)) continue;
                return AssetDatabase.LoadAssetAtPath<Material>(PaletteMaterialFolder + materialName + ".mat");
            }
            return null;
        }

        private void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith(PaletteMaterialFolder, StringComparison.Ordinal)) return;
            if (!assetPath.Contains(PaletteTextureName)) return;

            var importer = (TextureImporter)assetImporter;
            importer.textureType = TextureImporterType.Default;
            importer.filterMode = FilterMode.Point;
            importer.wrapMode = TextureWrapMode.Clamp;
            importer.mipmapEnabled = false;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.maxTextureSize = 256;
        }
    }
}
