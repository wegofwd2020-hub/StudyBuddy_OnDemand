"""
inject_g11_visuals.py — populate `section.visuals[]` in tutorial JSON for the
G11 Science demo, drawing from sample_content/ Option2_Catalogue + the
MP4s already rendered into web/public/sample-visuals/.

Idempotent: overwrites visuals[] on each run. Safe to re-run after the
pipeline rebuilds a tutorial.

Run from inside the celery-pipeline container so /data/content is writable:
  docker compose exec -T celery-pipeline python /app/scripts-repo/inject_g11_visuals.py

NOTE on MP4 paths: web/public/ is not mounted into celery-pipeline. The list
of available MP4s per unit is therefore hardcoded in UNIT_VIDEOS below — keep
in sync with files actually present at web/public/sample-visuals/{unit}/*.mp4.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

CURRICULUM_ID = "default-2026-g11-science"

# Inside celery-pipeline these paths exist as bind mounts.
CONTENT_ROOT = Path("/data/content")
SAMPLE_ROOT = Path("/app/sample_content/g11-science")

# web/public/ is not mounted in celery-pipeline; hardcode the MP4 filenames
# that exist at web/public/sample-visuals/{unit}/. Refresh after rendering
# new MP4s for a unit. Empty list = no video block injected.
UNIT_VIDEOS: dict[str, list[str]] = {
    "G11-PHYS-001": ["PhysicalWorld_ScaleOfUniverse.mp4"],
    "G11-PHYS-002": [
        "Kinematics_UAM.mp4",
        "Kinematics_FreeFall.mp4",
        "Kinematics_GraphAnalysis.mp4",
        "Kinematics_Projectile.mp4",
    ],
    "G11-PHYS-003": ["LawsOfMotion_NewtonSecond.mp4"],
    "G11-PHYS-004": ["WorkEnergy_RollerCoaster.mp4"],
    "G11-PHYS-005": ["RigidBody_AngularMomentum.mp4"],
    "G11-PHYS-006": ["Gravitation_KeplersSecond.mp4"],
    "G11-PHYS-007": ["BulkMatter_BernoulliVenturi.mp4"],
    "G11-PHYS-008": ["Thermo_CarnotCycle.mp4"],
    "G11-PHYS-009": ["KineticTheory_MaxwellBoltzmann.mp4"],
    "G11-PHYS-010": [
        "Oscillations_SHM.mp4",
        "Oscillations_Superposition.mp4",
        "Oscillations_Doppler.mp4",
    ],
    "G11-CHEM-001": ["BasicChem_MoleVisualization.mp4"],
    "G11-CHEM-002": [
        "StructureOfAtom_BohrTransition.mp4",
        "StructureOfAtom_ElectronFill.mp4",
    ],
    "G11-CHEM-003": ["Periodicity_TrendsWalkthrough.mp4"],
    "G11-CHEM-004": ["ChemBonding_VSEPRShapes.mp4"],
    "G11-CHEM-005": ["ChemThermo_ReactionCoordinate.mp4"],
    "G11-CHEM-006": ["Equilibrium_DynamicBalance.mp4"],
    "G11-CHEM-008": ["OrganicChem_FunctionalGroups.mp4"],
    "G11-MATH-001": ["Sets_and_Functions_Demo.mp4"],
    "G11-MATH-002": ["AdvancedAlgebra_QuadraticTransform.mp4"],
    "G11-MATH-003": ["CoordinateGeom_ConicSections.mp4"],
    "G11-MATH-004": ["Calculus_SecantToTangent.mp4"],
    "G11-MATH-005": ["Stats_NormalDistribution.mp4"],
    "G11-BIO-001": ["Diversity_TaxonomicHierarchy.mp4"],
    "G11-BIO-002": ["BioOrg_CellToOrganism.mp4"],
    "G11-BIO-003": ["CellBio_CellCycleWheel.mp4"],
    "G11-BIO-004": ["PlantPhysiol_PhotosynthesisFlow.mp4"],
    "G11-BIO-005": ["HumanPhysiol_CardiacCycle.mp4"],
    "G11-CHEM-007": ["Redox_GalvanicCell.mp4"],
    "G11-CHEM-009": ["Hydrocarbons_MarkovnikovAddition.mp4"],
}


@dataclass
class CoveredUnit:
    unit_id: str
    sample_dir_name: str
    # folder_to_section maps a folder under Option2_Catalogue/ to a tutorial
    # section_id (s1..sN). For units that follow `section-N-{slug}` naming we
    # leave this None and derive index-by-prefix.
    folder_to_section: dict[str, str] | None = None


COVERED_UNITS: list[CoveredUnit] = [
    # PHYS — all use section-N-{slug} folder convention
    CoveredUnit("G11-PHYS-001", "G11-PHYS-001_Physical_World_and_Measurement"),
    CoveredUnit("G11-PHYS-002", "G11-PHYS-002_Kinematics"),
    CoveredUnit("G11-PHYS-003", "G11-PHYS-003_Laws_of_Motion"),
    CoveredUnit("G11-PHYS-004", "G11-PHYS-004_Work_Energy_and_Power"),
    CoveredUnit("G11-PHYS-005", "G11-PHYS-005_Systems_of_Particles_and_Rigid_Bodies"),
    CoveredUnit("G11-PHYS-006", "G11-PHYS-006_Gravitation"),
    CoveredUnit("G11-PHYS-007", "G11-PHYS-007_Properties_of_Bulk_Matter"),
    CoveredUnit("G11-PHYS-008", "G11-PHYS-008_Thermodynamics"),
    CoveredUnit("G11-PHYS-009", "G11-PHYS-009_Kinetic_Theory"),
    CoveredUnit("G11-PHYS-010", "G11-PHYS-010_Oscillations_and_Waves"),
    # CHEM — all use section-N-{slug}
    CoveredUnit("G11-CHEM-001", "G11-CHEM-001_Some_Basic_Concepts_of_Chemistry"),
    CoveredUnit("G11-CHEM-002", "G11-CHEM-002_Structure_of_Atom"),
    CoveredUnit("G11-CHEM-003", "G11-CHEM-003_Periodicity"),
    CoveredUnit("G11-CHEM-004", "G11-CHEM-004_Chemical_Bonding"),
    CoveredUnit("G11-CHEM-005", "G11-CHEM-005_Chemical_Thermodynamics"),
    CoveredUnit("G11-CHEM-006", "G11-CHEM-006_Chemical_Equilibrium"),
    CoveredUnit("G11-CHEM-007", "G11-CHEM-007_Redox_Reactions"),
    CoveredUnit("G11-CHEM-008", "G11-CHEM-008_Organic_Chemistry_Basics"),
    CoveredUnit("G11-CHEM-009", "G11-CHEM-009_Hydrocarbons"),
    # MATH-001 uses topic folders; others use section-N
    CoveredUnit(
        unit_id="G11-MATH-001",
        sample_dir_name="G11-MATH-001_Sets_and_Functions",
        folder_to_section={
            "set-operations": "s1",
            "power-set": "s1",
            "katex-typography": "s1",
            "arrow-diagrams": "s2",
            "function-graphs": "s3",
            "composition": "s4",
            "animations": "s5",
        },
    ),
    CoveredUnit("G11-MATH-002", "G11-MATH-002_Advanced_Algebra"),
    CoveredUnit("G11-MATH-003", "G11-MATH-003_Coordinate_Geometry"),
    CoveredUnit("G11-MATH-004", "G11-MATH-004_Introduction_to_Calculus"),
    CoveredUnit("G11-MATH-005", "G11-MATH-005_Statistics_and_Probability"),
    # BIO — all use section-N-{slug}
    CoveredUnit("G11-BIO-001", "G11-BIO-001_Diversity_of_Living_Organisms"),
    CoveredUnit("G11-BIO-002", "G11-BIO-002_Structural_Organisation"),
    CoveredUnit("G11-BIO-003", "G11-BIO-003_Cell_Structure_and_Functions"),
    CoveredUnit("G11-BIO-004", "G11-BIO-004_Plant_Physiology"),
    CoveredUnit("G11-BIO-005", "G11-BIO-005_Human_Physiology"),
]


SMIL_TAG_RE = re.compile(rb"<(animate|animateTransform|animateMotion|set)\b")


def detect_kind(svg_path: Path, sidecar_kind: str) -> str:
    """Return 'animated-svg' if the SVG contains SMIL animation tags;
    otherwise return the sidecar's declared kind ('image' or 'image-grid')."""
    if sidecar_kind != "image":
        return sidecar_kind
    try:
        head = svg_path.read_bytes()[:8192]
    except OSError:
        return sidecar_kind
    return "animated-svg" if SMIL_TAG_RE.search(head) else "image"


def section_id_from_folder(folder: str, override: dict[str, str] | None) -> str | None:
    if override is not None:
        return override.get(folder)
    m = re.match(r"^section-(\d+)-", folder)
    return f"s{int(m.group(1))}" if m else None


def collect_visuals_for_unit(unit: CoveredUnit) -> dict[str, list[dict]]:
    """Walk Option2_Catalogue/ and return {section_id: [item, ...]}."""
    catalogue = SAMPLE_ROOT / unit.sample_dir_name / "Option2_Catalogue"
    if not catalogue.is_dir():
        print(f"  skip: {catalogue} missing")
        return {}

    by_section: dict[str, list[dict]] = {}
    for section_folder in sorted(catalogue.iterdir()):
        if not section_folder.is_dir():
            continue
        section_id = section_id_from_folder(section_folder.name, unit.folder_to_section)
        if section_id is None:
            print(f"  skip folder (no section mapping): {section_folder.name}")
            continue

        for sidecar in sorted(section_folder.glob("*.metadata.yaml")):
            svg_path = sidecar.with_suffix("").with_suffix(".svg")
            if not svg_path.exists():
                continue
            with sidecar.open() as f:
                meta = yaml.safe_load(f) or {}
            sidecar_kind = meta.get("kind", "image")
            kind = detect_kind(svg_path, sidecar_kind)
            topic_phrase = meta.get("topic_phrase", svg_path.stem)
            item = {
                "kind": kind,
                "src": f"/sample-visuals/{unit.unit_id}/{svg_path.name}",
                "alt": topic_phrase,
            }
            by_section.setdefault(section_id, []).append(item)
    return by_section


def find_unit_videos(unit: CoveredUnit) -> list[dict]:
    """Return MP4 items for the unit, sourced from UNIT_VIDEOS hardcoded list."""
    items: list[dict] = []
    for filename in UNIT_VIDEOS.get(unit.unit_id, []):
        name = Path(filename).stem.replace("_", " ").replace("-", " ")
        items.append({
            "kind": "video",
            "src": f"/sample-visuals/{unit.unit_id}/{filename}",
            "alt": name,
        })
    return items


def build_visual_blocks_for_section(items: list[dict]) -> list[dict]:
    """Group flat items by kind into VisualBlock dicts that match the web
    `VisualBlock` Pydantic shape: {kind, heading?, items: [{src, alt, caption?}]}."""
    if not items:
        return []
    blocks: list[dict] = []
    # Split by kind so video items become their own block, animated-svg becomes
    # its own (separate render branch in VisualSlot), and all images merge
    # into a single image-grid block when there are 2+.
    images = [i for i in items if i["kind"] == "image"]
    animated = [i for i in items if i["kind"] == "animated-svg"]
    videos = [i for i in items if i["kind"] == "video"]

    if videos:
        blocks.append({
            "kind": "video",
            "heading": "Watch this concept",
            "items": [{"src": v["src"], "alt": v["alt"]} for v in videos],
        })
    if animated:
        for v in animated:
            blocks.append({
                "kind": "animated-svg",
                "heading": "Animated diagram",
                "items": [{"src": v["src"], "alt": v["alt"]}],
            })
    if images:
        if len(images) == 1:
            blocks.append({
                "kind": "image",
                "items": [{"src": v["src"], "alt": v["alt"]} for v in images],
            })
        else:
            blocks.append({
                "kind": "image-grid",
                "items": [{"src": v["src"], "alt": v["alt"]} for v in images],
            })
    return blocks


def inject_unit(unit: CoveredUnit) -> bool:
    """Mutate tutorial_en.json for a unit. Return True on success."""
    tutorial_path = CONTENT_ROOT / "curricula" / CURRICULUM_ID / unit.unit_id / "tutorial_en.json"
    if not tutorial_path.exists():
        print(f"  ERROR: {tutorial_path} missing — pipeline may not have written it yet")
        return False

    by_section = collect_visuals_for_unit(unit)
    videos = find_unit_videos(unit)
    if videos:
        by_section.setdefault("s1", [])
        by_section["s1"] = videos + by_section["s1"]  # videos before images

    if not by_section:
        print(f"  no visuals found for {unit.unit_id}")
        return False

    with tutorial_path.open() as f:
        tutorial = json.load(f)

    sections = tutorial.get("sections", [])
    n_total_blocks = 0
    n_total_items = 0
    for section in sections:
        sid = section.get("section_id")
        items = by_section.get(sid, [])
        blocks = build_visual_blocks_for_section(items)
        section["visuals"] = blocks  # always overwrite for idempotency
        n_total_blocks += len(blocks)
        n_total_items += sum(len(b["items"]) for b in blocks)

    # Atomic write
    tmp_path = tutorial_path.with_suffix(".tmp")
    with tmp_path.open("w") as f:
        json.dump(tutorial, f, indent=2)
    os.replace(tmp_path, tutorial_path)

    print(f"  {unit.unit_id}: {n_total_blocks} blocks, {n_total_items} items across {len(by_section)} sections")
    return True


def main() -> int:
    print(f"Injecting visuals into tutorial JSON for {len(COVERED_UNITS)} units in {CURRICULUM_ID}")
    success = 0
    for unit in COVERED_UNITS:
        print(f"\n→ {unit.unit_id}")
        if inject_unit(unit):
            success += 1
    print(f"\nDone: {success}/{len(COVERED_UNITS)} units updated")
    return 0 if success == len(COVERED_UNITS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
