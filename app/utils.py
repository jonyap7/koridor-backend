import math

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def marginal_cost_km(start, pickup, drop, end):
    direct = haversine_km(start[0], start[1], end[0], end[1])
    with_order = haversine_km(start[0], start[1], pickup[0], pickup[1]) +                  haversine_km(pickup[0], pickup[1], drop[0], drop[1]) +                  haversine_km(drop[0], drop[1], end[0], end[1])
    return max(0.0, with_order - direct)

def estimate_minutes(km: float, avg_kmh: float = 35.0) -> float:
    return (km / avg_kmh) * 60.0
