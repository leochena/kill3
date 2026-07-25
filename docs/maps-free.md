# Free / open map stack (recommended)

free-match **does not depend** on a paid map SDK. Coordinates are WGS84 in `where.geo`. Display and geocoding should stay swappable and preferably free/open.

## What we use in the reference UI today

| Piece | Choice | Cost / terms |
|-------|--------|----------------|
| Map tiles | **OpenStreetMap** raster via community tile URL in Leaflet | Free for reasonable use; **self-host or use a compliant provider for production** — do not hammer `tile.openstreetmap.org` at scale ([OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/)) |
| Map JS | **Leaflet** (BSD) | Free |
| Distance | **Haversine** in `fmlib` / API | Free, offline |
| Browser locate | `navigator.geolocation` | Free, user permission |

## Free geocoding / search options

| Service | Use | Notes |
|---------|-----|--------|
| **Nominatim** (OSM) | address → lat/lon | Free public instance has strict limits; **self-host** or use a provider that runs Nominatim |
| **Photon** | autocomplete | OSM-based, open source |
| **Compass / Pelias** | geocoder stack | Self-host |
| Manual map pick | UI click | Always available offline-ish |

**Agent rule:** if geocoding fails, keep `region` text and ask user to map-pick or paste coordinates. Never block listing.

## Production-friendly free/cheap tile hosts (examples)

Operators should pick one and document attribution:

- Self-hosted **TileServer GL** / OpenMapTiles  
- Community providers that allow open-source apps (check current ToS)  
- Offline region packs for field use  

Set via env (reference server/UI can read later):

```bash
FM_TILE_URL=https://your-tiles/{z}/{x}/{y}.png
FM_TILE_ATTR=© OpenStreetMap contributors
FM_NOMINATIM_URL=https://your-nominatim/search
```

## What not to do

- Hard-require Google/Mapbox paid keys in mainline  
- Sell “map pins” or paid placement on the map  
- Store precise home addresses as `privacy: public` without user consent  

## Privacy

Default listing privacy `after_deal` for fine address; shop pins may be `public`.  
See protocol `where.privacy`.

## Implementation status

| Feature | Status |
|---------|--------|
| Leaflet + OSM tiles in reference UI | ✅ |
| Haversine distance API/CLI | ✅ |
| Map pick + browser GPS | ✅ |
| Nominatim helper in CLI | ⏳ `fm geocode` planned — see roadmap |
| Configurable tile URL | ⏳ env wiring |

Detail: [roadmaps/maps.md](roadmaps/maps.md).
