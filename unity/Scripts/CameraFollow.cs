using UnityEngine;

/// <summary>
/// Simple chase camera. Attach to the Main Camera and assign the ship as target.
/// </summary>
public class CameraFollow : MonoBehaviour
{
    public Transform target;
    public Vector3 offset = new Vector3(0f, 8f, -18f);
    public float followSeconds = 0.3f;

    private Vector3 _vel;

    void LateUpdate()
    {
        if (target == null) return;

        Vector3 desiredPos = target.position + target.rotation * offset;
        transform.position = Vector3.SmoothDamp(transform.position, desiredPos, ref _vel, followSeconds);
        transform.LookAt(target.position + Vector3.up * 1.5f);
    }
}
