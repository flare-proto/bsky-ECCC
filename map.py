import geopandas
import matplotlib.pyplot as plt
import contextily as ctx

geojson_dict = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "coordinates": [
                    [
                        [-114.30495502380798, 51.02662872874069],
                        [-114.27789598447181, 50.974123679163625],
                        [-114.07720810939594, 50.955661851736664],
                        [-114.18093442685056, 51.080490997731914],
                        [-114.30495502380798, 51.02662872874069]
                    ]
                ],
                "type": "Polygon"
            }
        }
    ]
}

# Load GeoJSON and project to Web Mercator
gdf = geopandas.GeoDataFrame.from_features(geojson_dict["features"], crs="EPSG:4326")
gdf_web_mercator = gdf.to_crs(epsg=3857)

# Compute bounds and small padding
minx, miny, maxx, maxy = gdf_web_mercator.total_bounds
x_pad = (maxx - minx) * 0.01
y_pad = (maxy - miny) * 0.01

# Create ultra-wide figure
fig, ax = plt.subplots(figsize=(64,64))

# Plot
gdf_web_mercator.plot(ax=ax, color='red', alpha=0.7)

# Set axis limits before adding basemap so contextily knows how many tiles to fetch
ax.set_xlim(minx - x_pad, maxx + x_pad)
ax.set_ylim(miny - y_pad, maxy + y_pad)

# Add OSM tiles that cover entire area
ctx.add_basemap(ax, crs=gdf_web_mercator.crs, source=ctx.providers.OpenStreetMap.Mapnik,zoom=7)

# Clean up axes
ax.set_xticks([])
ax.set_yticks([])
ax.axis('off')

# Save normally (without bbox_inches='tight')
plt.savefig("geojson_with_osm.png", dpi=300)
