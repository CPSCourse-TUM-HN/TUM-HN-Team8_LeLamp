from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MJCF = ROOT / "simulation/robot.xml"
TARGET_MJCF = ROOT / "simulation/ailamp_robot.xml"
REMOVED_BASE_MESHES = {"lamp_base", "lamp_base_cover"}
REPLACEMENT_BASE_ASSETS = {
    "ailamp_base_arm_link_boot_mesh": "ailamp_adapters/AILamp_Base_Arm_Link_Boot.stl",
}


def _add_replacement_mesh_assets(root: ET.Element) -> None:
    asset = root.find("asset")
    if asset is None:
        asset = ET.SubElement(root, "asset")
    existing = {mesh.attrib.get("name") for mesh in asset.findall("mesh")}
    for name, filename in REPLACEMENT_BASE_ASSETS.items():
        if name not in existing:
            ET.SubElement(
                asset,
                "mesh",
                {
                    "name": name,
                    "file": filename,
                    "scale": "0.001 0.001 0.001",
                },
            )


def _remove_and_replace_matching_geoms(parent: ET.Element) -> int:
    removed = 0
    replacements: dict[str, dict[str, str]] = {}
    for child in list(parent):
        if child.tag == "geom" and child.attrib.get("mesh") in REMOVED_BASE_MESHES:
            mesh_name = child.attrib["mesh"]
            if child.attrib.get("class") == "visual" and mesh_name not in replacements:
                replacements[mesh_name] = {
                    "pos": child.attrib["pos"],
                    "quat": child.attrib["quat"],
                }
            parent.remove(child)
            removed += 1
        else:
            removed += _remove_and_replace_matching_geoms(child)

    transform = replacements.get("lamp_base_cover") or replacements.get("lamp_base")
    if transform is not None:
        ET.SubElement(
            parent,
            "geom",
            {
                "name": "ailamp_base_arm_link_boot_visual",
                "type": "mesh",
                "class": "visual",
                "pos": transform["pos"],
                "quat": transform["quat"],
                "mesh": "ailamp_base_arm_link_boot_mesh",
                "material": "ailamp_cover_gray",
                "contype": "0",
                "conaffinity": "0",
            },
        )
    return removed


def generate_ailamp_robot(
    source_path: Path = SOURCE_MJCF,
    target_path: Path = TARGET_MJCF,
) -> int:
    tree = ET.parse(source_path)
    root = tree.getroot()
    removed = _remove_and_replace_matching_geoms(root)
    if removed == 0:
        raise RuntimeError(f"no base geoms removed from {source_path}")
    _add_replacement_mesh_assets(root)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(target_path, encoding="utf-8", xml_declaration=True)
    return removed


if __name__ == "__main__":
    removed_count = generate_ailamp_robot()
    print(f"{TARGET_MJCF.relative_to(ROOT)} removed_base_geoms={removed_count}")
