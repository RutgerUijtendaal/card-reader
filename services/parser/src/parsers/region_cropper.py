from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

from settings import settings


class RegionCropper:
    def crop_regions(
        self,
        *,
        image_path: Path,
        template: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        regions = template.get("regions")
        if not isinstance(regions, dict) or not regions:
            raise ValueError("Template has no valid regions")

        template_width = self._as_int(template.get("card_width"))
        template_height = self._as_int(template.get("card_height"))
        region_crops: dict[str, dict[str, Any]] = {}

        with Image.open(image_path) as image:
            width, height = image.size
            for region_name, region_spec in regions.items():
                x, y, w, h = self._resolve_bbox(
                    region_spec=region_spec,
                    image_width=width,
                    image_height=height,
                    template_width=template_width,
                    template_height=template_height,
                )
                cropped = image.crop((x, y, x + w, y + h)).copy()
                region_crops[region_name] = {"x": x, "y": y, "w": w, "h": h, "image": cropped}

        return region_crops

    def write_debug_crops(
        self,
        *,
        template_id: str,
        checksum: str,
        image_path: Path,
        region_crops: dict[str, dict[str, Any]],
    ) -> None:
        output_dir = settings.debug_crops_dir / template_id / checksum
        output_dir.mkdir(parents=True, exist_ok=True)
        for region_name, crop in region_crops.items():
            output_path = output_dir / f"{region_name}.png"
            crop_image = crop["image"]
            if isinstance(crop_image, Image.Image):
                crop_image.save(output_path)

        metadata_path = output_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(
                {
                    "source_file": str(image_path),
                    "template_id": template_id,
                    "checksum": checksum,
                    "regions": {
                        name: {"x": crop["x"], "y": crop["y"], "w": crop["w"], "h": crop["h"]}
                        for name, crop in region_crops.items()
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _resolve_bbox(
        self,
        *,
        region_spec: Any,
        image_width: int,
        image_height: int,
        template_width: int | None,
        template_height: int | None,
    ) -> tuple[int, int, int, int]:
        if isinstance(region_spec, dict):
            return self._resolve_bbox_from_object(
                region_spec=region_spec,
                image_width=image_width,
                image_height=image_height,
            )

        if isinstance(region_spec, list) and len(region_spec) == 4:
            x = self._as_int(region_spec[0]) or 0
            y = self._as_int(region_spec[1]) or 0
            w = self._as_int(region_spec[2]) or image_width
            h = self._as_int(region_spec[3]) or image_height
            if template_width and template_height:
                x = int(round((x / template_width) * image_width))
                y = int(round((y / template_height) * image_height))
                w = int(round((w / template_width) * image_width))
                h = int(round((h / template_height) * image_height))
            return self._clamp_bbox(x=x, y=y, w=w, h=h, image_width=image_width, image_height=image_height)

        raise ValueError("Invalid region specification. Expected object or [x,y,w,h] list.")

    def _resolve_bbox_from_object(
        self,
        *,
        region_spec: dict[str, Any],
        image_width: int,
        image_height: int,
    ) -> tuple[int, int, int, int]:
        unit = str(region_spec.get("unit", "relative")).lower()
        x_raw = float(region_spec.get("x", 0.0))
        y_raw = float(region_spec.get("y", 0.0))
        w_raw = float(region_spec.get("w", 1.0))
        h_raw = float(region_spec.get("h", 1.0))

        if unit == "relative":
            x = int(round(x_raw * image_width))
            y = int(round(y_raw * image_height))
            w = int(round(w_raw * image_width))
            h = int(round(h_raw * image_height))
            return self._clamp_bbox(x=x, y=y, w=w, h=h, image_width=image_width, image_height=image_height)

        if unit == "absolute":
            return self._clamp_bbox(
                x=int(round(x_raw)),
                y=int(round(y_raw)),
                w=int(round(w_raw)),
                h=int(round(h_raw)),
                image_width=image_width,
                image_height=image_height,
            )

        raise ValueError(f"Unsupported region unit '{unit}'.")

    def _clamp_bbox(
        self,
        *,
        x: int,
        y: int,
        w: int,
        h: int,
        image_width: int,
        image_height: int,
    ) -> tuple[int, int, int, int]:
        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        w = max(1, min(w, image_width - x))
        h = max(1, min(h, image_height - y))
        return x, y, w, h

    def _as_int(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(round(value))
        return None
