using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// Unity's side of "multiple consumers, one twin". This polls the same
/// api/server.py that wraps model.twin.ShipTwin -- Unity never talks to the
/// simulator or the SQLite store directly, same rule the Streamlit dashboard
/// follows, just over HTTP instead of an in-process call.
///
/// Attach to the GameObject that represents the ship. lat/lon are converted
/// to a local flat-earth XZ plane relative to refLat/refLon (an equirectangular
/// approximation -- fine over the ~100nm scale of this route, would need a
/// proper projection for anything much larger) and scaled down so the route
/// fits a normal Unity scene instead of literal meters.
/// </summary>
public class TwinClient : MonoBehaviour
{
    [Header("API")]
    public string apiUrl = "http://localhost:8000/twin/snapshot";
    public float pollIntervalSeconds = 1f;

    [Header("Reference origin (Le Havre -- WAYPOINTS[0] in ship_simulator.py)")]
    public double refLat = 49.4938;
    public double refLon = 0.1077;

    [Header("Scale")]
    [Tooltip("1 Unity unit = this many real meters.")]
    public float metersPerUnit = 200f;

    [Tooltip("Seconds to glide to each new position/rotation instead of snapping.")]
    public float smoothSeconds = 1f;

    public ShipSnapshot Latest { get; private set; }

    private Vector3 _targetPos;
    private Quaternion _targetRot;
    private bool _hasTarget;

    void Start()
    {
        _targetPos = transform.position;
        _targetRot = transform.rotation;
        StartCoroutine(PollLoop());
    }

    void Update()
    {
        if (!_hasTarget) return;
        float t = smoothSeconds > 0f ? Time.deltaTime / smoothSeconds : 1f;
        transform.position = Vector3.Lerp(transform.position, _targetPos, t);
        transform.rotation = Quaternion.Slerp(transform.rotation, _targetRot, t);
    }

    IEnumerator PollLoop()
    {
        var wait = new WaitForSeconds(pollIntervalSeconds);
        while (true)
        {
            yield return Fetch();
            yield return wait;
        }
    }

    IEnumerator Fetch()
    {
        using (UnityWebRequest req = UnityWebRequest.Get(apiUrl))
        {
            yield return req.SendWebRequest();
            if (req.result != UnityWebRequest.Result.Success)
            {
                Debug.LogWarning($"TwinClient: request failed ({apiUrl}): {req.error}");
                yield break;
            }

            ShipSnapshot snap;
            try
            {
                snap = JsonUtility.FromJson<ShipSnapshot>(req.downloadHandler.text);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"TwinClient: failed to parse snapshot: {e.Message}");
                yield break;
            }

            Latest = snap;
            SetTargetFromSnapshot(snap);
        }
    }

    void SetTargetFromSnapshot(ShipSnapshot snap)
    {
        double x = (snap.lon - refLon) * Math.Cos(refLat * Math.PI / 180.0) * 111_320.0;
        double z = (snap.lat - refLat) * 110_540.0;

        _targetPos = new Vector3((float)(x / metersPerUnit), transform.position.y, (float)(z / metersPerUnit));
        // heading_deg is compass bearing (0=N, 90=E); with +Z mapped to north and
        // +X to east above, rotating that many degrees around Y lines up directly.
        _targetRot = Quaternion.Euler(0f, snap.heading_deg, 0f);
        _hasTarget = true;
    }
}
