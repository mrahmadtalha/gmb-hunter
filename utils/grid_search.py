"""
GRID SEARCH UTILITY
Divides any city in the world into a geographic grid.
Each grid cell becomes a separate Google Maps search.

How it works:
1. Get city center coordinates from OpenStreetMap (free, no API key)
2. Get city bounding box (north/south/east/west limits)
3. Divide bounding box into NxN grid cells
4. Each cell = one search query using lat/lng coordinates
5. Combine all results, remove duplicates

Works for ANY city worldwide, ANY business type.
"""

import os
import sys
import math
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import log_info, log_success, log_warning, log_error


def get_city_bounds(city: str) -> dict | None:
    """
    Get city bounding box from OpenStreetMap Nominatim API.
    Returns: {lat_min, lat_max, lng_min, lng_max, center_lat, center_lng}
    Free, no API key needed.
    """
    try:
        url    = "https://nominatim.openstreetmap.org/search"
        params = {
            "q":              city,
            "format":         "json",
            "limit":          1,
            "addressdetails": 1,
        }
        headers = {"User-Agent": "GMBHunter/1.0 (business data collector)"}

        response = requests.get(url, params=params, headers=headers, timeout=10)
        data     = response.json()

        if not data:
            log_warning(f"City not found: {city}")
            return None

        result   = data[0]
        bbox     = result.get("boundingbox", [])  # [lat_min, lat_max, lng_min, lng_max]

        if len(bbox) < 4:
            log_warning(f"No bounding box for: {city}")
            return None

        lat_min = float(bbox[0])
        lat_max = float(bbox[1])
        lng_min = float(bbox[2])
        lng_max = float(bbox[3])

        center_lat = (lat_min + lat_max) / 2
        center_lng = (lng_min + lng_max) / 2

        log_success(f"City bounds found: {city}")
        log_info(f"  Lat: {lat_min:.4f} → {lat_max:.4f}")
        log_info(f"  Lng: {lng_min:.4f} → {lng_max:.4f}")
        log_info(f"  Center: {center_lat:.4f}, {center_lng:.4f}")

        return {
            "lat_min":    lat_min,
            "lat_max":    lat_max,
            "lng_min":    lng_min,
            "lng_max":    lng_max,
            "center_lat": center_lat,
            "center_lng": center_lng,
            "city_name":  result.get("display_name", city).split(",")[0],
        }

    except Exception as e:
        log_error(f"Could not get city bounds for '{city}': {e}")
        return None


def generate_grid(bounds: dict, grid_size: int = 4) -> list:
    """
    Divide city bounding box into grid_size x grid_size cells.
    Returns list of (center_lat, center_lng) for each cell.

    grid_size=4 → 4x4 = 16 cells → ~320 potential records
    grid_size=5 → 5x5 = 25 cells → ~500 potential records
    """
    lat_min = bounds["lat_min"]
    lat_max = bounds["lat_max"]
    lng_min = bounds["lng_min"]
    lng_max = bounds["lng_max"]

    lat_step = (lat_max - lat_min) / grid_size
    lng_step = (lng_max - lng_min) / grid_size

    cells = []
    for i in range(grid_size):
        for j in range(grid_size):
            cell_lat = lat_min + (i + 0.5) * lat_step
            cell_lng = lng_min + (j + 0.5) * lng_step
            cells.append({
                "lat":  round(cell_lat, 6),
                "lng":  round(cell_lng, 6),
                "row":  i + 1,
                "col":  j + 1,
                "cell": f"R{i+1}C{j+1}",
            })

    log_info(f"Grid created: {grid_size}x{grid_size} = {len(cells)} cells")
    return cells


def get_grid_for_city(city: str, target: int = 100) -> list:
    """
    Main function: get grid cells for a city.
    Automatically calculates grid size based on target records.

    target=50  → 3x3 grid (9 cells)
    target=100 → 4x4 grid (16 cells)
    target=200 → 5x5 grid (25 cells)
    target=500 → 7x7 grid (49 cells)
    """
    # Calculate grid size needed
    # Each cell returns ~20 results on average
    cells_needed = math.ceil(target / 20)
    grid_size    = max(3, math.ceil(math.sqrt(cells_needed)))
    grid_size    = min(grid_size, 8)  # cap at 8x8 = 64 cells max

    log_info(f"Target: {target} records → Grid: {grid_size}x{grid_size} = {grid_size**2} cells")

    bounds = get_city_bounds(city)
    if not bounds:
        log_warning(f"Could not get bounds for {city}. Using fallback search.")
        return []

    time.sleep(1)  # be polite to Nominatim API
    return generate_grid(bounds, grid_size)


if __name__ == "__main__":
    # Test
    cells = get_grid_for_city("Lahore", target=100)
    print(f"\nGrid cells for Lahore ({len(cells)} total):")
    for cell in cells[:5]:
        print(f"  Cell {cell['cell']}: lat={cell['lat']}, lng={cell['lng']}")
    print(f"  ... and {len(cells)-5} more")