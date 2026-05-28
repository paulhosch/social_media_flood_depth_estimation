# Image Geolocation: State of the Art (2025/2026)

## Two Distinct Problems

Image geolocation spans two fundamentally different tasks with very different accuracy ceilings.

**Open-world geolocation** asks "where on Earth was this taken?" from a single image without any reference data. Current best systems achieve kilometer-scale accuracy on average, with sub-kilometer in favorable (urban, landmark-rich) conditions. Consistent meter-level accuracy for arbitrary images remains out of reach.

**Visual localization** asks "where exactly within a mapped area?" by matching a query image against a pre-built, geo-referenced database (e.g. Google Street View, SfM point clouds, satellite imagery). Here, meter to sub-meter accuracy is routinely demonstrated, and centimeter-level is achievable in controlled settings.

## Key Methods and Accuracy

| Approach | Typical Accuracy | Reference Data Needed | Key Examples |
|---|---|---|---|
| SfM + feature matching | cm to sub-meter | Pre-built 3D map | hloc, COLMAP, LightGlue, SuperGlue |
| Street View cross-matching | ~1 m | GSV panoramas | Block-wise matching (Purdue, 2024) |
| Cross-view (ground to satellite) | 1–5 m | Satellite imagery + coarse GPS | VIGOR, BEV-based methods |
| NeRF-based localization | ~7 cm (vs. LiDAR GT) | NeRF model of area | LocoNeRF (2023) |
| Planet-scale classification | median ~44 km | None (standalone model) | PIGEON / PIGEOTTO (CVPR 2024) |
| LVLMs with chain-of-thought | best case ~300 m, typical km | None | ETHAN, ChatGPT o3 |
| Commercial OSINT tools | city / neighborhood | None | GeoSpy (Graylark) |

## Ready-to-Use Products

| Product | Accuracy | Type | Cost | Setup Effort |
|---|---|---|---|---|
| Google ARCore Geospatial API | ~1–5 m (often ~1 m) | Mobile SDK (live camera) | Free (quota-based) | Medium |
| Niantic Lightship VPS | cm-level (at scanned sites) | Mobile SDK (live camera) | Free tier + paid | Medium |
| hloc (open source) | cm to sub-meter | Self-hosted pipeline | Free | High |
| GeoSpy | City / neighborhood | Web tool + REST API | Free tier + paid plans | Very low |
| ChatGPT / LLMs | km-scale, sometimes better | Chat / API | Subscription | Very low |

## Can You Achieve Meter-Level Accuracy?

**Yes, if** you have a geo-referenced reference database (Street View, your own SfM reconstruction, or satellite imagery) and use structure-based matching with geometric verification. Google's ARCore Geospatial API is the most accessible path, providing ~1 m accuracy globally wherever Street View coverage exists. Niantic's VPS reaches centimeter-level at pre-scanned locations.

**Not yet, if** you need to geolocate arbitrary images "blindly" without any reference database. The best open-world systems (PIGEON, ETHAN, ChatGPT o3) operate at kilometer scale on average, with occasional sub-kilometer hits in visually distinctive urban scenes.

## Key References

- Haas et al., "PIGEON: Predicting Image Geolocations," CVPR 2024
- Li et al., "ETHAN: Image-Based Geolocation Using Large Vision-Language Models," arXiv 2408.09474
- Sarlin et al., hloc (Hierarchical Localization), github.com/cvg/Hierarchical-Localization
- Nenashev et al., "LocoNeRF: NeRF-based Local SfM for Precise Localization," arXiv 2310.05134
- Fervers, "Visual Cross-view Geolocalization," PhD thesis, KIT 2024
- Google ARCore Geospatial API: developers.google.com/ar/develop/geospatial
- MMS-VPR dataset and benchmark: arXiv 2505.12254 (2025)
