# Flood depth estimation from social media and street-level images

## Summary of research landscape (May 2026)

This document summarizes the state of image-based flood water level estimation, starting from the EcoVision Lab (ETH Zürich) work and covering the current landscape of publicly available tools.

---

## Origin: EcoVision Lab, ETH Zürich

The EcoVision Lab (Photogrammetry and Remote Sensing group, ETH Zürich) published foundational work on estimating flood water levels from social media images. The lead researcher was Priyanka Chaudhary, supervised by Jan Dirk Wegner and Konrad Schindler, with collaborators at Eawag (Swiss Federal Institute of Aquatic Science and Technology).

The core idea: detect common objects of known dimensions (people, cars, bicycles, houses, buses) in flood images, quantify how submerged they are on a 0 to 10 scale, and convert that to a metric water depth estimate.

### Key publications

| Year | Paper | Method | Performance |
|------|-------|--------|-------------|
| 2019 | Flood-Water Level Estimation from Social Media Images (ISPRS Annals, Best Paper Award) | Mask R-CNN with flood level prediction head, instance segmentation | 8.07 cm RMSE, 1268 images |
| 2020 | Water level prediction with a multi-task ranking approach (ISPRS J. Photogramm. Remote Sens.) | Per-image regression + pairwise ranking loss (PyTorch) | ~11 cm RMSE, 8145 images (DeepFlood dataset) |
| 2022 | Flood Uncertainty Estimation Using Deep Ensembles (Water) | Deep ensembles for flood hazard maps at 1 m resolution | 21 cm MAE for extreme cases |

### Code availability from EcoVision

- **ETH GitLab** (`gitlab.ethz.ch/pchaudha/flood_level_instance` and `/master-thesis`): requires ETH LDAP authentication, not publicly accessible.
- **GitHub** (`github.com/priyanka-chaudhary`): three public repos.
  - `water_level_with_ranking`: PyTorch code for the 2020 paper, includes training scripts and annotations. No pretrained weights. Dataset available only by email request.
  - `flood_level_instance`: Jupyter notebooks for the 2019 Mask R-CNN approach.
  - `uncertainty_flood`: Jupyter notebooks for the 2022 deep ensembles paper.
- **Verdict**: research-grade code, no pretrained models, no deployment pipeline, dataset requires email request to an address that may be stale.

---

## Current landscape (2024 to 2026)

### Implementation-ready tools

**STURM-FloodDepth (2025)**
- Authors: Notarangelo et al., EU Marie Curie (MSCA) Postdoctoral Fellowship project
- Pipeline: YOLO-World + SAHI for vehicle detection, EDSR super-resolution, fine-tuned ResNet-50 for flood level classification (5 classes), SuperGlue + RANSAC for georeferencing, GeoJSON output
- Code: `github.com/STURM-WEO/STURM-FloodDepth`
- Data: 3367 cropped vehicle images on Zenodo (DOI: 10.5281/zenodo.14833532)
- Status: pipeline-ready, includes trained ResNet-50 weights and curated dataset
- Note: the STURM project also provides STURM-Flood, a Sentinel-1/Sentinel-2 flood extent mapping dataset (`github.com/STURM-WEO/STURM-Flood`)

**FLOOD-DEPTH-ML (2026)**
- Authors: Mishra et al.
- Method: YOLOv8/v11 vehicle submergence classifier with a Python GUI
- Code: `github.com/mayankmi/FLOOD-DEPTH-ML` (Apache 2.0)
- Includes: pretrained weights (`best_car.pt` for YOLOv8, `best_car_YOLOv11.pt`), `requirements.txt`, single-file script
- Features: image, video, YouTube link, and live webcam analysis with color-coded risk levels and sound alerts
- Status: turnkey, the most deployment-ready option available

### State-of-the-art (paper only, no code released)

**FloodLlama (2025, preprint)**
- Authors: Fuad and Qian, Wayne State University
- Method: LLaMA 3.2-11B Vision fine-tuned with QLoRA on ~190,000 synthetic images (7 vehicle types, 4 weather conditions, 41 depth levels at 1 cm resolution)
- Performance: MAE < 0.97 cm, Acc@5cm > 93.7% (on synthetic test data)
- Status: no code, no model weights, no dataset released

**FloodVision (2025)**
- Authors: Liu et al., Georgia Institute of Technology
- Method: zero-shot GPT-4o + domain knowledge graph (FloodKG in RDF) for reference object identification and submergence ratio estimation
- Performance: 8.17 cm MAE on 110 crowdsourced images (MyCoast New York)
- Status: no code released, requires OpenAI API access

---

## Comparative overview

| Project | Code | Weights | Data | Readiness |
|---------|------|---------|------|-----------|
| EcoVision (2019/2020) | GitHub (partial) | No | Email request | Research only |
| STURM-FloodDepth (2025) | GitHub | Yes (ResNet-50) | Zenodo | Pipeline-ready |
| FLOOD-DEPTH-ML (2026) | GitHub | Yes (YOLOv8/v11) | Demo included | Turnkey |
| FloodLlama (2025) | No | No | No | Paper only |
| FloodVision (2025) | No | No | No | Paper only |

---

## Key takeaways

1. The EcoVision work was pioneering but remains research-grade with no deployment path.
2. The field has bifurcated into (a) YOLO-based vehicle submergence classifiers that are practical and deployable, and (b) vision-language model approaches (FloodLlama, FloodVision) that show superior accuracy but lack released implementations.
3. For immediate use, FLOOD-DEPTH-ML is plug-and-play. For a research pipeline with georeferenced outputs, STURM-FloodDepth is the best option.
4. The VLM-based approaches represent the likely future direction, as they generalize across diverse reference objects without needing custom object detectors, but none are currently reproducible.
