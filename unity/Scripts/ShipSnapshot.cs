using System;

/// <summary>
/// Mirrors api.server.Snapshot field-for-field. JsonUtility deserializes by
/// matching field names, so this has to stay in sync with the Python side --
/// there's no schema negotiation, just a shared contract both ends agree to.
/// </summary>
[Serializable]
public class ShipSnapshot
{
    public double lat;
    public double lon;
    public float heading_deg;
    public float speed_knots;
    public float rpm;
    public float fuel_level_l;
    public float fuel_rate_lph;
    public float fuel_pct;
    public float engine_temp_c;
    public int waypoint_idx;
    public float distance_to_next_wp_nm;
    public float eta_next_wp_hours;
    public float fuel_range_nm;
    public float avg_fuel_rate_lph;
    public float sim_time_s;
    public float fouling_pct;
}
