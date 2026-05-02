from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Dict, Mapping, Optional

try:
    from overstats.src.modules.errors import ModuleError
except ModuleNotFoundError:
    from src.modules.errors import ModuleError

from .render import RenderedImage, render_patch_fallback, render_patch_notes
from .requests import (
    PATCH_TRANSLATION_CACHE_VERSION,
    PatchNotesRequests,
    build_patch_cache_key,
    build_sources_summary,
    build_summary_text,
    choose_source,
    deserialize_patch_candidate,
    normalize_patch_kind,
    serialize_patch_candidate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_ROOT = PROJECT_ROOT / "cache" / "patch_notes"
PATCH_NOTES_UNAVAILABLE_MESSAGE = "OW 补丁说明暂时不可用。"


@dataclass(frozen=True)
class PatchNotesOutput:
    requested_kind: str
    selected_kind: str
    source: str
    source_name: str
    translated: bool
    summary: str
    selected: Dict[str, Any]
    sources: Dict[str, Dict[str, str]]
    image: Optional[RenderedImage] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "requested_kind": self.requested_kind,
            "selected_kind": self.selected_kind,
            "source": self.source,
            "source_name": self.source_name,
            "translated": self.translated,
            "summary": self.summary,
            "selected": serialize_patch_candidate(self.selected),
            "sources": self.sources,
        }


class PatchNotesModule:
    def __init__(
        self,
        requests: Optional[PatchNotesRequests] = None,
        *,
        cache_root: Path | str | None = None,
        time_provider: Optional[Callable[[], float]] = None,
        date_provider: Optional[Callable[[], dt.date]] = None,
        renderer: Optional[Callable[..., RenderedImage]] = None,
        fallback_renderer: Optional[Callable[..., RenderedImage]] = None,
    ) -> None:
        self.requests = requests or PatchNotesRequests()
        self.cache_root = Path(cache_root or DEFAULT_CACHE_ROOT)
        self.time_provider = time_provider or time.time
        self.date_provider = date_provider or dt.date.today
        self.renderer = renderer or render_patch_notes
        self.fallback_renderer = fallback_renderer or render_patch_fallback
        self.asset_dir = self.cache_root / "images"

    async def query_patch_notes(self, *, patch_kind: Any = None, render: bool = False) -> PatchNotesOutput:
        try:
            requested_kind = normalize_patch_kind(patch_kind)
        except ValueError as exc:
            raise ModuleError(
                error="invalid_patch_kind",
                message=str(exc),
                status_code=400,
                hint='Example: {"patch_kind":"small"}',
            ) from exc

        slot_key = requested_kind
        cn_slots, en_slots = await self.requests.scan_sources(now_date=self.date_provider())
        chosen_source = choose_source(cn_slots, en_slots, slot_key=slot_key)
        if chosen_source is None:
            raise ModuleError(
                error="patch_notes_unavailable",
                message=PATCH_NOTES_UNAVAILABLE_MESSAGE,
                status_code=502,
                details={
                    "requested_kind": requested_kind,
                    "sources": build_sources_summary(cn_slots, en_slots),
                },
            )

        chosen_slots = cn_slots if chosen_source == "cn" else en_slots
        selected_patch = dict(chosen_slots[slot_key])
        summary_text = build_summary_text(cn_slots, en_slots, selected_patch)
        sources_summary = build_sources_summary(cn_slots, en_slots)

        render_candidate = dict(selected_patch)
        translated = False
        cached_image_bytes: Optional[bytes] = None
        cache_key = build_patch_cache_key(selected_patch)

        if chosen_source == "en":
            cached_bundle = self._load_cached_patch_bundle(cache_key)
            if cached_bundle is not None:
                cached_candidate = cached_bundle.get("candidate")
                if isinstance(cached_candidate, dict):
                    render_candidate = cached_candidate
                    translated = bool(cached_bundle.get("translated"))
                cached_image_bytes = cached_bundle.get("image")
            else:
                try:
                    render_candidate, translated = await self.requests.translate_patch_candidate(selected_patch)
                except Exception as exc:
                    print(f"[overstats] patch_notes translation failed: {type(exc).__name__}: {exc}")
                    render_candidate = dict(selected_patch)
                    translated = False

        output = PatchNotesOutput(
            requested_kind=requested_kind,
            selected_kind=slot_key,
            source=str(render_candidate.get("source") or chosen_source),
            source_name=str(render_candidate.get("source_name") or ""),
            translated=translated,
            summary=summary_text,
            selected=render_candidate,
            sources=sources_summary,
        )
        if not render:
            return output

        if cached_image_bytes:
            return PatchNotesOutput(
                requested_kind=output.requested_kind,
                selected_kind=output.selected_kind,
                source=output.source,
                source_name=output.source_name,
                translated=output.translated,
                summary=output.summary,
                selected=output.selected,
                sources=output.sources,
                image=RenderedImage(content=cached_image_bytes),
            )

        image = await self._render_candidate(output.selected, output.summary)
        if chosen_source == "en" and translated and image is not None:
            self._save_cached_patch_bundle(cache_key, output.selected, output.summary, image.content, translated=True)

        return PatchNotesOutput(
            requested_kind=output.requested_kind,
            selected_kind=output.selected_kind,
            source=output.source,
            source_name=output.source_name,
            translated=output.translated,
            summary=output.summary,
            selected=output.selected,
            sources=output.sources,
            image=image,
        )

    async def _render_candidate(self, candidate: Mapping[str, Any], summary_text: str) -> RenderedImage:
        use_proxy = str(candidate.get("source") or "") == "en"
        try:
            asset_paths = await self.requests.cache_images(self._collect_asset_urls(candidate), self.asset_dir, use_proxy=use_proxy)
            return self.renderer(candidate, summary_text=summary_text, asset_paths=asset_paths)
        except RuntimeError as exc:
            print(f"[overstats] patch_notes structured render unavailable: {type(exc).__name__}: {exc}")
        except Exception as exc:
            print(f"[overstats] patch_notes structured render failed: {type(exc).__name__}: {exc}")

        try:
            return self.fallback_renderer(candidate, summary_text=summary_text)
        except RuntimeError as exc:
            raise ModuleError(
                error="render_dependency_missing",
                message=str(exc),
                status_code=500,
                hint="Install Pillow in the runtime environment to enable patch note image rendering.",
            ) from exc
        except Exception as exc:
            raise ModuleError(
                error="patch_notes_render_failed",
                message=f"Patch notes image generation failed: {type(exc).__name__}: {exc}",
                status_code=500,
            ) from exc

    def _cache_paths(self, cache_key: str) -> tuple[Path, Path]:
        self.cache_root.mkdir(parents=True, exist_ok=True)
        base_path = self.cache_root / cache_key
        return base_path.with_suffix(".json"), base_path.with_suffix(".png")

    def _load_cached_patch_bundle(self, cache_key: str) -> Optional[Dict[str, Any]]:
        metadata_path, image_path = self._cache_paths(cache_key)
        if not metadata_path.exists() or not image_path.exists():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("cache_version") != PATCH_TRANSLATION_CACHE_VERSION:
                return None
            return {
                "translated": bool(metadata.get("translated")),
                "candidate": deserialize_patch_candidate(metadata.get("candidate")),
                "summary": str(metadata.get("summary") or ""),
                "image": image_path.read_bytes(),
            }
        except Exception as exc:
            print(f"[overstats] failed to read patch_notes cache {metadata_path}: {type(exc).__name__}: {exc}")
            return None

    def _save_cached_patch_bundle(
        self,
        cache_key: str,
        candidate: Mapping[str, Any],
        summary_text: str,
        image_bytes: bytes,
        *,
        translated: bool,
    ) -> None:
        metadata_path, image_path = self._cache_paths(cache_key)
        payload = {
            "cache_version": PATCH_TRANSLATION_CACHE_VERSION,
            "translated": bool(translated),
            "summary": summary_text,
            "candidate": serialize_patch_candidate(candidate),
            "saved_at": self._format_generated_at(self.time_provider()),
        }
        self._write_json_atomic(metadata_path, payload)
        self._write_bytes_atomic(image_path, image_bytes)

    def _collect_asset_urls(self, candidate: Mapping[str, Any]) -> list[str]:
        urls = []
        seen = set()

        def add(url: Any) -> None:
            normalized = str(url or "").strip()
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            urls.append(normalized)

        for section in candidate.get("sections") or []:
            for hero_update in section.get("hero_updates") or []:
                add(hero_update.get("icon_url"))
                for ability in hero_update.get("abilities") or []:
                    add(ability.get("icon_url"))
            for map_update in section.get("map_updates") or []:
                add(map_update.get("before_image_url"))
                add(map_update.get("after_image_url"))
        return urls

    def _write_json_atomic(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix="patch-notes.", suffix=".json", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
                file.write("\n")
            Path(temp_path).replace(path)
        finally:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except OSError:
                pass

    def _write_bytes_atomic(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix="patch-notes.", suffix=path.suffix, dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as file:
                file.write(content)
            Path(temp_path).replace(path)
        finally:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except OSError:
                pass

    def _format_generated_at(self, timestamp: float) -> str:
        return dt.datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d %H:%M:%S")


patch_notes_module = PatchNotesModule()
