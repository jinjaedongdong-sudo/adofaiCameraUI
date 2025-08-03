using System.Collections.Generic;
using BepInEx;
using UnityEngine;

namespace CameraEditorMod
{
    /// <summary>
    /// Simple mod showcasing a custom easing timeline with layered offsets.
    ///
    /// The implementation is intentionally lightweight but follows the
    /// structure outlined in the FLOWERs Mod Development Guide.  A playback
    /// camera is driven by an <see cref="AnimationCurve"/> that can be edited at
    /// runtime.  Multiple offset layers may be stacked which are summed during
    /// evaluation.  The timeline can be scrubbed through a horizontal slider.
    /// </summary>
    [BepInPlugin("com.example.cameraeditor", "Camera Editor Mod", "0.2.0")]
    public class CameraEditorMod : BaseUnityPlugin
    {
        private Camera editorCamera;
        private Camera playbackCamera;
        private AudioSource musicSource;

        // base position captured from the editor camera
        private Vector3 basePosition;

        // timeline state
        private float timeline;
        private bool isPlaying;

        // editable easing curve and layered offsets
        private AnimationCurve customEase = AnimationCurve.Linear(0, 0, 1, 1);
        private readonly List<Vector3> offsetLayers = new();

        private void Start()
        {
            editorCamera = Camera.main;
            playbackCamera = new GameObject("PlaybackCamera").AddComponent<Camera>();
            playbackCamera.enabled = false;

            musicSource = gameObject.AddComponent<AudioSource>();

            if (editorCamera != null)
            {
                basePosition = editorCamera.transform.position;
            }
        }

        // Triggered when the user starts playback
        public void BeginPlayback()
        {
            if (editorCamera != null)
            {
                editorCamera.enabled = false;
            }

            if (playbackCamera != null)
            {
                playbackCamera.enabled = true;
                playbackCamera.transform.position = basePosition;
            }

            if (musicSource != null)
            {
                musicSource.Play();
            }

            timeline = 0f;
            isPlaying = true;
        }

        // Triggered when playback ends
        public void EndPlayback()
        {
            isPlaying = false;

            if (playbackCamera != null)
            {
                playbackCamera.enabled = false;
            }

            if (editorCamera != null)
            {
                editorCamera.enabled = true;
            }

            if (musicSource != null)
            {
                musicSource.Stop();
            }
        }

        private void Update()
        {
            if (!isPlaying || playbackCamera == null)
            {
                return;
            }

            timeline += Time.deltaTime;
            float easedT = customEase.Evaluate(Mathf.Clamp01(timeline));

            Vector3 totalOffset = Vector3.zero;
            foreach (var layer in offsetLayers)
            {
                totalOffset += layer;
            }

            playbackCamera.transform.position = basePosition + totalOffset;

            if (timeline >= 1f)
            {
                EndPlayback();
            }
        }

        private void OnGUI()
        {
            GUILayout.BeginArea(new Rect(10, 10, 300, 400), "Custom Easing", GUI.skin.window);

            GUILayout.Label("Timeline");
            float newTimeline = GUILayout.HorizontalSlider(timeline, 0f, 1f);
            if (!isPlaying)
            {
                timeline = newTimeline;
            }

            GUILayout.Space(10);

            GUILayout.Label("Offset Layers");
            if (GUILayout.Button("Add Layer"))
            {
                offsetLayers.Add(Vector3.zero);
            }

            for (int i = 0; i < offsetLayers.Count; i++)
            {
                GUILayout.BeginHorizontal();
                GUILayout.Label($"#{i}", GUILayout.Width(20));
                offsetLayers[i].x = GUILayout.HorizontalSlider(offsetLayers[i].x, -5f, 5f);
                offsetLayers[i].y = GUILayout.HorizontalSlider(offsetLayers[i].y, -5f, 5f);
                offsetLayers[i].z = GUILayout.HorizontalSlider(offsetLayers[i].z, -5f, 5f);
                if (GUILayout.Button("X", GUILayout.Width(20)))
                {
                    offsetLayers.RemoveAt(i);
                    GUILayout.EndHorizontal();
                    break;
                }
                GUILayout.EndHorizontal();
            }

            GUILayout.Space(10);
            GUILayout.Label("Ease Keys (t,value)");
            if (GUILayout.Button("Add Key"))
            {
                customEase.AddKey(timeline, 0f);
            }

            Keyframe[] keys = customEase.keys;
            for (int i = 0; i < keys.Length; i++)
            {
                GUILayout.BeginHorizontal();
                GUILayout.Label(i.ToString(), GUILayout.Width(20));
                float t = GUILayout.HorizontalSlider(keys[i].time, 0f, 1f);
                float v = GUILayout.HorizontalSlider(keys[i].value, 0f, 1f);
                keys[i].time = t;
                keys[i].value = v;
                customEase.MoveKey(i, keys[i]);
                if (GUILayout.Button("X", GUILayout.Width(20)))
                {
                    customEase.RemoveKey(i);
                    GUILayout.EndHorizontal();
                    break;
                }
                GUILayout.EndHorizontal();
            }

            GUILayout.EndArea();
        }
    }
}
