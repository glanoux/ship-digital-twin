using UnityEditor;
using UnityEngine;

/// <summary>
/// One-click low-poly ship, built from Unity's own primitives -- no external
/// asset, no custom mesh/winding code that would be easy to get wrong
/// unseen. Menu: Tools > Build Simple Ship. Replaces any existing "Ship"
/// GameObject and attaches TwinClient to the new one, so the whole
/// composite moves/rotates together once it starts polling.
///
/// The ship's un-rotated bow points along local +Z (Unity's default
/// "forward"), matching TwinClient's heading_deg -> Quaternion.Euler(0,
/// heading_deg, 0) mapping -- see TwinClient.cs.
/// </summary>
public static class ShipModelBuilder
{
    static readonly Color Red = new Color(0.55f, 0.07f, 0.07f);
    static readonly Color White = new Color(0.92f, 0.92f, 0.92f);
    static readonly Color Dark = new Color(0.08f, 0.08f, 0.09f);
    static readonly Color Gray = new Color(0.28f, 0.28f, 0.3f);

    [MenuItem("Tools/Build Simple Ship")]
    public static void BuildShip()
    {
        var existing = GameObject.Find("Ship");
        if (existing != null) Object.DestroyImmediate(existing);

        const float width = 2.2f;       // beam
        const float hullLength = 6.5f;
        const float lowerH = 0.55f;     // below waterline (red)
        const float upperH = 0.85f;     // freeboard (white)

        var root = new GameObject("Ship");

        float hullBottomY = -(lowerH + upperH) / 2f;
        float lowerCenterY = hullBottomY + lowerH / 2f;
        float upperCenterY = hullBottomY + lowerH + upperH / 2f;
        float hullTopY = hullBottomY + lowerH + upperH;
        float hullFrontZ = hullLength / 2f;

        AddBox(root.transform, "HullLower", new Vector3(width, lowerH, hullLength),
            new Vector3(0f, lowerCenterY, 0f), Quaternion.identity, Red);
        AddBox(root.transform, "HullUpper", new Vector3(width, upperH, hullLength),
            new Vector3(0f, upperCenterY, 0f), Quaternion.identity, White);

        // A square rotated 45deg around Y is widest exactly through its own
        // center, not at its edge -- so placing it flush with the hull's front
        // face makes it flare out past the hull, not taper to a point. Setting
        // the square's side to the hull's beam and offsetting its center back
        // by width*(sqrt(2)-1)/2 makes the diamond's width match the hull's
        // beam exactly at the seam, so only the forward, narrowing half (a
        // clean point extending width/2 beyond the bow) is visible.
        float bowCenterZ = hullFrontZ - width * (Mathf.Sqrt(2f) - 1f) / 2f;
        var bowRot = Quaternion.Euler(0f, 45f, 0f);
        AddBox(root.transform, "BowLower", new Vector3(width, lowerH, width),
            new Vector3(0f, lowerCenterY, bowCenterZ), bowRot, Red);
        AddBox(root.transform, "BowUpper", new Vector3(width, upperH, width),
            new Vector3(0f, upperCenterY, bowCenterZ), bowRot, White);

        // Tiered bridge, stepping in toward the stern.
        var tier1Scale = new Vector3(1.6f, 0.9f, 2.2f);
        var tier1Pos = new Vector3(0f, hullTopY + tier1Scale.y / 2f, -hullLength * 0.25f);
        AddBox(root.transform, "BridgeTier1", tier1Scale, tier1Pos, Quaternion.identity, White);
        float tier1TopY = tier1Pos.y + tier1Scale.y / 2f;
        float tier1FrontZ = tier1Pos.z + tier1Scale.z / 2f;

        var tier2Scale = new Vector3(1.1f, 0.7f, 1.4f);
        var tier2Pos = new Vector3(0f, tier1TopY + tier2Scale.y / 2f, tier1Pos.z - 0.1f);
        AddBox(root.transform, "BridgeTier2", tier2Scale, tier2Pos, Quaternion.identity, White);
        float tier2TopY = tier2Pos.y + tier2Scale.y / 2f;

        // Window band on the tier-1 bridge front, offset just past the face to avoid z-fighting.
        AddBox(root.transform, "BridgeWindows", new Vector3(tier1Scale.x - 0.1f, 0.28f, 0.04f),
            new Vector3(0f, tier1Pos.y, tier1FrontZ + 0.03f), Quaternion.identity, Dark);

        AddCylinder(root.transform, "FunnelBody", new Vector3(0.4f, 0.5f, 0.4f),
            new Vector3(0f, tier2TopY + 0.5f, tier2Pos.z), Gray);
        AddCylinder(root.transform, "FunnelBand", new Vector3(0.43f, 0.12f, 0.43f),
            new Vector3(0f, tier2TopY + 1.0f + 0.12f, tier2Pos.z), Red);

        AddCylinder(root.transform, "Mast", new Vector3(0.08f, 0.9f, 0.08f),
            new Vector3(0f, hullTopY + 0.9f, tier1FrontZ + 0.5f), Dark);
        AddBox(root.transform, "Yardarm", new Vector3(0.9f, 0.06f, 0.06f),
            new Vector3(0f, hullTopY + 1.5f, tier1FrontZ + 0.5f), Quaternion.identity, Dark);

        // Scaling the root (rather than every child's numbers) blows up the
        // whole composite uniformly -- children's local positions/sizes are
        // already relative to it. TwinClient sets world *position* on this
        // same transform, which scale doesn't affect, so this is safe to
        // change independently of where the ship actually sits.
        root.transform.localScale = Vector3.one * ShipScale;

        root.AddComponent<TwinClient>();
        ConfigureCameraAndOcean(root.transform, hullLength * ShipScale);

        Selection.activeGameObject = root;
        Debug.Log($"Built 'Ship' at {ShipScale}x scale. Delete any placeholder Cube, " +
                   "then press Play.");
    }

    const float ShipScale = 100f;

    // Camera offset and ocean-plane size were tuned for the ship at its
    // original (1x) size; blowing the ship up without touching them would
    // put the camera inside the hull and the ship through the edges of the
    // sea. Kept proportional to ship length so this still looks right
    // whatever ShipScale is set to.
    static void ConfigureCameraAndOcean(Transform ship, float scaledLength)
    {
        var cam = Camera.main != null ? Camera.main.gameObject : GameObject.Find("Main Camera");
        if (cam != null)
        {
            var follow = cam.GetComponent<CameraFollow>();
            if (follow == null) follow = cam.AddComponent<CameraFollow>();
            follow.target = ship;
            follow.offset = new Vector3(0f, scaledLength * (8f / 6.5f), -scaledLength * (18f / 6.5f));
        }

        var ocean = GameObject.Find("Plane");
        if (ocean != null)
        {
            float desiredWorldSize = scaledLength * 6f;
            float currentWorldSize = ocean.transform.localScale.x * 10f; // default Plane mesh is 10x10 at scale 1
            if (currentWorldSize < desiredWorldSize)
            {
                float s = desiredWorldSize / 10f;
                ocean.transform.localScale = new Vector3(s, ocean.transform.localScale.y, s);
            }
        }
    }

    static GameObject AddBox(Transform parent, string name, Vector3 scale, Vector3 localPos, Quaternion localRot, Color color)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.localScale = scale;
        go.transform.localPosition = localPos;
        go.transform.localRotation = localRot;
        go.GetComponent<MeshRenderer>().sharedMaterial = MakeMaterial(color);
        return go;
    }

    static GameObject AddCylinder(Transform parent, string name, Vector3 scale, Vector3 localPos, Color color)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.localScale = scale;
        go.transform.localPosition = localPos;
        go.GetComponent<MeshRenderer>().sharedMaterial = MakeMaterial(color);
        return go;
    }

    static Material MakeMaterial(Color color)
    {
        Shader shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
        var mat = new Material(shader);
        if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
        else if (mat.HasProperty("_Color")) mat.SetColor("_Color", color);
        return mat;
    }
}
