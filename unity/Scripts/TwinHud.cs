using UnityEngine;

/// <summary>
/// Deliberately uses OnGUI (Unity's built-in immediate-mode GUI) instead of
/// the Canvas/TextMeshPro UI system, so there's zero scene setup: attach this
/// to any GameObject and point it at the TwinClient, done. Good enough for a
/// debug readout; a real UI would use Canvas + TMP.
/// </summary>
public class TwinHud : MonoBehaviour
{
    public TwinClient client;

    void OnGUI()
    {
        if (client == null || client.Latest == null) return;
        var s = client.Latest;

        GUI.Box(new Rect(10, 10, 260, 160), "Ship Digital Twin");
        GUI.Label(new Rect(20, 35, 240, 20), $"Speed: {s.speed_knots:F1} kn");
        GUI.Label(new Rect(20, 55, 240, 20), $"Heading: {s.heading_deg:F0} deg");
        GUI.Label(new Rect(20, 75, 240, 20), $"RPM: {s.rpm:F0}");
        GUI.Label(new Rect(20, 95, 240, 20), $"Fuel: {s.fuel_pct:F1}%");
        GUI.Label(new Rect(20, 115, 240, 20), $"Engine temp: {s.engine_temp_c:F1} C");
        GUI.Label(new Rect(20, 135, 240, 20), $"Fouling (ground truth): {s.fouling_pct:F1}%");
    }
}
