from __future__ import annotations

import asyncio
import importlib
import json
import os
import shutil
import sys
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig

_PLUGIN_DIR = Path(__file__).resolve().parent
_PLUGIN_ROOT_STR = str(_PLUGIN_DIR)
if _PLUGIN_ROOT_STR not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT_STR)

from overstats.paths import get_overstats_data_dir, get_plugin_data_dir

_OVERSTATS_ROOT = _PLUGIN_DIR / "overstats"
_RES_DIR = _OVERSTATS_ROOT / "res"
_PLUGIN_DATA_DIR = get_plugin_data_dir()
_OVERSTATS_DATA_DIR = get_overstats_data_dir()
_BINDINGS_PATH = _PLUGIN_DATA_DIR / "bindings.json"
_TEMP_IMAGE_DIR = _PLUGIN_DATA_DIR / "temp"

_CN_MODE_MAP = {"快速": "quick", "竞技": "competitive"}
_CN_RANK_MAP = {
    "全部": "all", "青铜": "Bronze", "白银": "Silver", "黄金": "Gold",
    "铂金": "Platinum", "钻石": "Diamond", "大师": "Master",
    "宗师": "Grandmaster", "冠军": "Champion",
}
_CN_PATCH_KIND_MAP = {"最新": "latest", "小更新": "small", "大更新": "big"}


def _flatten_config(config: AstrBotConfig) -> dict:
    return {
        "dashen_accounts": list(config.get("dashen_accounts", [])),
        "dashen_global": config.get("dashen_global", {}),
        "network": config.get("network", {}),
        "analysis": config.get("analysis", {}),
        "output": config.get("output", {}),
        "permissions": config.get("permissions", {}),
        "features": config.get("features", {}),
    }


class OwDashenPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config
        self._api_client = None
        self._bnet_search = None
        self._profile = None
        self._match = None
        self._rank_history = None
        self._quick_strength = None
        self._competitive_strength = None
        self._summary = None
        self._pick_rate = None
        self._hero_leaderboard_sync = None
        self._shop = None
        self._patch_notes = None
        self._identity_search = None

    def _account_features_ready(self) -> bool:
        return self._api_client is not None and self._bnet_search is not None

    def _account_not_configured_hint(self) -> str:
        return "插件已加载，但你还没有在插件配置里填写可用的网易大神账号。请先到 AstrBot 插件配置面板中，填写至少一个启用的 role_id 和 token，然后重载插件。"

    async def initialize(self) -> None:
        flat = _flatten_config(self.config)
        from overstats.config import config as overstats_config_module
        overstats_config_module.inject_config(flat)

        from overstats.src.modules.ow_hero_leaderboard.service import OWHeroLeaderboardSyncService
        self._hero_leaderboard_sync = OWHeroLeaderboardSyncService()
        try:
            await self._hero_leaderboard_sync.sync_once()
            await self._hero_leaderboard_sync.start()
        except Exception as e:
            logger.warning(f"[ow_dashen] 英雄热度数据初始化失败: {e}")

        from overstats.src.modules.ow_hero_pick_rate.service import OWHeroPickRateModule
        self._pick_rate = OWHeroPickRateModule()

        from overstats.src.modules.ow_shop.service import OWShopModule
        self._shop = OWShopModule()

        from overstats.src.modules.patch_notes.service import PatchNotesModule
        self._patch_notes = PatchNotesModule()

        from overstats.src.modules.player_identity_search.service import PlayerIdentitySearchModule
        self._identity_search = PlayerIdentitySearchModule()

        try:
            from overstats.config.loader import get_dashen_client_config
            client_config = get_dashen_client_config()

            from overstats.src.client.apiclient import init_dashen_api_client
            self._api_client = init_dashen_api_client(client_config)

            from overstats.src.modules.bnet_search.service import BnetSearchModule
            self._bnet_search = BnetSearchModule(self._api_client)

            from overstats.src.modules.dashen_profile.service import DashenProfileModule
            self._profile = DashenProfileModule(self._api_client, search_module=self._bnet_search)

            from overstats.src.modules.dashen_match.service import DashenMatchModule
            self._match = DashenMatchModule(self._api_client, search_module=self._bnet_search)

            from overstats.src.modules.dashen_rank_history.service import DashenRankHistoryModule
            self._rank_history = DashenRankHistoryModule(self._api_client, search_module=self._bnet_search)

            from overstats.src.modules.dashen_quick_strength.service import DashenQuickStrengthModule
            self._quick_strength = DashenQuickStrengthModule(self._api_client, search_module=self._bnet_search)

            from overstats.src.modules.dashen_competitive_strength.service import DashenCompetitiveStrengthModule
            self._competitive_strength = DashenCompetitiveStrengthModule(self._api_client, search_module=self._bnet_search)

            from overstats.src.modules.dashen_summary.service import DashenSummaryModule
            self._summary = DashenSummaryModule(search_module=self._bnet_search)
        except ValueError as e:
            logger.warning(f"[ow_dashen] 插件已加载，但大神账号尚未配置完成: {e}")
            self._api_client = None
            self._bnet_search = None
            self._profile = None
            self._match = None
            self._rank_history = None
            self._quick_strength = None
            self._competitive_strength = None
            self._summary = None

        logger.info("[ow_dashen] 插件初始化完成，所有模块已加载")

    async def terminate(self) -> None:
        if self._hero_leaderboard_sync is not None:
            try:
                await self._hero_leaderboard_sync.close()
            except Exception as e:
                logger.warning(f"[ow_dashen] 关闭英雄热度同步任务时出错: {e}")
        if self._api_client is not None:
            from overstats.src.client.apiclient import close_default_clients
            try:
                await close_default_clients()
            except Exception as e:
                logger.warning(f"[ow_dashen] 关闭 API 客户端时出错: {e}")
        logger.info("[ow_dashen] 插件已终止")

    def _normalize_optional_text(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _coerce_int(self, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        text = str(value).strip()
        if text and text.lstrip("+-").isdigit():
            return int(text)
        return None

    def _split_optional_battletag_and_number(self, battletag_or_number: object, number: object) -> tuple[str | None, int | None]:
        explicit_number = self._coerce_int(number)
        first_number = self._coerce_int(battletag_or_number)
        if first_number is not None and explicit_number is None:
            return None, first_number
        return self._normalize_optional_text(battletag_or_number), explicit_number

    def _sync_summary_runtime_client(self) -> None:
        if self._api_client is None:
            return
        try:
            from overstats.src.modules.dashen_summary import engine as summary_engine
            summary_engine.dashen_api_client = self._api_client
            runtime = getattr(summary_engine, "_RUNTIME", None)
            if runtime is not None:
                runtime.dashen.dashen_api_client = self._api_client
        except Exception as e:
            logger.debug(f"[ow_dashen] 同步总结运行时客户端失败: {e}")

    async def _ensure_query_tool_assets_ready(self) -> None:
        try:
            from overstats.src.modules.query_tool.service import ensure_query_tool_assets, load_query_tool
            config = load_query_tool(force_refresh=False)
            if not config:
                return
            await asyncio.to_thread(ensure_query_tool_assets, config)
        except Exception as e:
            logger.warning(f"[ow_dashen] 预加载 query_tool 素材失败，部分图片元素可能缺失: {e}")

    async def _resolve_battletag(self, event: AstrMessageEvent, explicit_tag: object = None) -> str | None:
        tag = self._normalize_optional_text(explicit_tag)
        if tag:
            return tag
        sender_id = str(event.get_sender_id() or "")
        return self._read_bindings().get(sender_id)

    async def _set_bind(self, sender_id: str, battletag: str) -> None:
        bindings = self._read_bindings()
        bindings[str(sender_id)] = str(battletag).strip()
        self._write_bindings(bindings)

    async def _remove_bind(self, sender_id: str) -> None:
        bindings = self._read_bindings()
        bindings.pop(str(sender_id), None)
        self._write_bindings(bindings)

    async def _get_bind(self, sender_id: str) -> str | None:
        return self._read_bindings().get(str(sender_id))

    def _read_bindings(self) -> dict[str, str]:
        if not _BINDINGS_PATH.exists():
            return {}
        try:
            payload = json.loads(_BINDINGS_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[ow_dashen] 读取 bindings.json 失败: {e}")
            return {}
        if not isinstance(payload, dict):
            return {}
        result: dict[str, str] = {}
        for key, value in payload.items():
            sender_id = str(key or "").strip()
            battletag = str(value or "").strip()
            if sender_id and battletag:
                result[sender_id] = battletag
        return result

    def _write_bindings(self, bindings: dict[str, str]) -> None:
        _PLUGIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
        normalized = {str(k): str(v) for k, v in bindings.items() if str(k).strip() and str(v).strip()}
        _BINDINGS_PATH.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _format_rank_history_fallback(self, seasons: list[dict]) -> list[str]:
        lines: list[str] = []
        for season_info in seasons:
            season_num = season_info.get("season", "?")
            competitive = season_info.get("competitive") or {}
            roles = competitive.get("roles") or []
            if not roles:
                lines.append(f"  赛季 {season_num}: 无竞技段位数据")
                continue

            role_parts: list[str] = []
            for role in roles:
                role_type = str(role.get("role_type") or "").strip()
                current = role.get("current") or {}
                peak = role.get("peak") or {}
                current_score = int(current.get("rank_score") or 0)
                peak_score = int(peak.get("rank_score") or 0)
                current_sub_tier = int(current.get("rank_sub_tier") or 0)
                peak_sub_tier = int(peak.get("rank_sub_tier") or 0)
                match_sum = int(role.get("match_sum") or 0)
                win_rate = float(role.get("win_rate") or 0)
                role_label = {"tank": "坦克", "dps": "输出", "healer": "辅助", "open": "开放"}.get(role_type, role_type or "未知")
                role_parts.append(
                    f"{role_label} 当前{current_score}/{current_sub_tier} 最高{peak_score}/{peak_sub_tier} 场次{match_sum} 胜率{win_rate:.1f}%"
                )

            lines.append(f"  赛季 {season_num}: " + "；".join(role_parts))
        return lines

    def _no_bind_hint(self) -> str:
        return "你还没有绑定守望先锋账号。请先使用 /ow 绑定 <BattleTag> 绑定你的账号，例如 /ow 绑定 BattleTag#1234"

    async def _save_and_send_image(self, event: AstrMessageEvent, rendered, fallback_text: str = "") -> None:
        if rendered is None:
            if fallback_text:
                yield event.plain_result(fallback_text)
            return
        try:
            _TEMP_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            img_path = _TEMP_IMAGE_DIR / f"{hash(rendered.content)}.png"
            img_path.write_bytes(rendered.content)
            yield event.image_result(str(img_path))
            if self.config.get("output", {}).get("cleanup_temp_files", True):
                try:
                    img_path.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"[ow_dashen] 图片发送失败: {e}")
            if fallback_text:
                yield event.plain_result(fallback_text)

    def _cn_mode_to_en(self, mode: str) -> str:
        return _CN_MODE_MAP.get(mode.strip(), mode.strip().lower())

    def _cn_rank_to_en(self, rank: str) -> str:
        return _CN_RANK_MAP.get(rank.strip(), rank.strip())

    def _cn_patch_kind_to_en(self, kind: str) -> str:
        return _CN_PATCH_KIND_MAP.get(kind.strip(), kind.strip().lower())

    @filter.command("owhelp")
    async def owhelp(self, event: AstrMessageEvent, command_name: str | None = None):
        '''查看守望先锋大神插件的全部命令和用法'''
        if not command_name:
            text = (
                "OW 大神插件命令表\n"
                "================\n"
                "提示：已绑定用户可省略 [BattleTag]。\n"
                "格式：<> 必填，[] 可选。\n"
                "\n"
                "【账号】\n"
                "  /ow 绑定 <BattleTag>\n"
                "    绑定守望先锋账号\n"
                "  /ow 解绑\n"
                "    解绑当前账号\n"
                "  /ow 我的绑定\n"
                "    查看当前绑定\n"
                "\n"
                "【玩家数据】\n"
                "  /ow 资料 [BattleTag]\n"
                "    玩家资料、头像、段位概览\n"
                "  /ow 战绩 [BattleTag] [场数]\n"
                "    最近战绩列表；场数 1-20，默认 5\n"
                "  /ow 对局详情 [BattleTag] <序号>\n"
                "    单场详细数据；序号来自战绩列表\n"
                "  /ow 段位 [BattleTag]\n"
                "    多赛季段位历史\n"
                "  /ow 快速强度 [BattleTag] [场数]\n"
                "    快速模式强度分析；场数 3-12，默认 5\n"
                "  /ow 竞技强度 [BattleTag] [场数]\n"
                "    竞技模式强度分析；场数 3-12，默认 5\n"
                "\n"
                "【总结】\n"
                "  /ow 今日总结 [BattleTag]\n"
                "  /ow 昨日总结 [BattleTag]\n"
                "  /ow 本周总结 [BattleTag]\n"
                "    生成对局总结图；本周总结可能较慢\n"
                "\n"
                "【英雄 / 商店 / 补丁】\n"
                "  /ow 英雄热度 [模式] [段位]\n"
                "    模式：快速/竞技；段位：全部到冠军\n"
                "  /ow 英雄曲线 <英雄名> [模式] [段位]\n"
                "    单英雄选取率历史曲线\n"
                "  /ow 商店\n"
                "    当前守望先锋商店\n"
                "  /ow 补丁 [类型]\n"
                "    类型：最新/小更新/大更新\n"
                "\n"
                "【搜索与维护】\n"
                "  /ow 搜索玩家 <关键词>\n"
                "    从本地缓存搜索 BattleTag 候选\n"
                "  /ow 自检\n"
                "    [管理员] 检查账号、客户端和素材缓存\n"
                "  /ow 清理缓存\n"
                "    [管理员] 清理图片和总结缓存\n"
                "\n"
                "查看单条命令帮助：owhelp <命令名>\n"
                "例如：owhelp 战绩"
            )
            yield event.plain_result(text)
            return

        cmd = command_name.strip().lower()
        help_map = {
            "绑定": "绑定你的守望先锋账号，绑定后无需重复输入 BattleTag。\n用法：/ow 绑定 <BattleTag>\n示例：/ow 绑定 BattleTag#1234\n注意：BattleTag 格式为\"名字#数字\"。",
            "解绑": "解绑你的守望先锋账号。\n用法：/ow 解绑",
            "我的绑定": "查看你当前绑定的守望先锋账号 BattleTag。\n用法：/ow 我的绑定",
            "资料": "查玩家资料。优先返回资料图；如果图片失败，会退回到简要文字结果。\n用法：/ow 资料 [BattleTag]\n示例：/ow 资料、/ow 资料 BattleTag#1234",
            "战绩": "查最近战绩列表，默认查 5 场。\n用法：/ow 战绩 [BattleTag] [场数]\n场数范围 1-20，默认 5。\n示例：/ow 战绩、/ow 战绩 10",
            "对局详情": "查单场对局详细数据。\n用法：/ow 对局详情 [BattleTag] <序号>\n序号从最近战绩列表里按从新到旧排列（1=最近一场）。\n当前主命令默认返回一张详情图。\n示例：/ow 对局详情 1",
            "段位": "查各赛季段位历史变化。\n用法：/ow 段位 [BattleTag]",
            "快速强度": "查快速模式强度分析。\n用法：/ow 快速强度 [BattleTag] [场数]\n场数范围 3-12，默认 5。",
            "竞技强度": "查竞技模式强度分析。\n用法：/ow 竞技强度 [BattleTag] [场数]\n场数范围 3-12，默认 5。",
            "今日总结": "查今日总结。\n用法：/ow 今日总结 [BattleTag]",
            "昨日总结": "查昨日总结。\n用法：/ow 昨日总结 [BattleTag]",
            "本周总结": "查本周总结（数据量大，需较长时间）。\n用法：/ow 本周总结 [BattleTag]",
            "英雄热度": "查英雄选取率榜单。\n用法：/ow 英雄热度 [模式] [段位]\n模式：快速/竞技；段位：全部/青铜/白银/黄金/铂金/钻石/大师/宗师/冠军\n示例：/ow 英雄热度 竞技 大师",
            "英雄曲线": "查单英雄选取率历史曲线。\n用法：/ow 英雄曲线 <英雄名> [模式] [段位]\n示例：/ow 英雄曲线 安娜 竞技 大师",
            "商店": "查当前守望先锋商店。\n用法：/ow 商店",
            "补丁": "查补丁说明。\n用法：/ow 补丁 [类型]\n类型：最新/小更新/大更新\n示例：/ow 补丁 大更新",
            "搜索玩家": "搜索玩家。\n用法：/ow 搜索玩家 <关键词>\n示例：/ow 搜索玩家 Nickname",
            "自检": "[管理员] 检查账号配置、客户端状态和素材缓存。\n用法：/ow 自检",
            "清理缓存": "[管理员] 清理本地图片缓存和总结运行时缓存。\n用法：/ow 清理缓存",
        }
        detail = help_map.get(cmd)
        if detail:
            yield event.plain_result(detail)
        else:
            yield event.plain_result(f"未找到命令 \"{command_name}\" 的帮助。使用 /owhelp 查看所有可用命令。")

    @filter.command_group("ow")
    def ow(self):
        '''守望先锋大神数据查询'''
        pass

    @ow.command("绑定")
    async def ow_bind(self, event: AstrMessageEvent, battletag: str):
        '''绑定你的守望先锋账号 BattleTag'''
        tag = battletag.strip()
        if not tag or "#" not in tag:
            yield event.plain_result("BattleTag 格式不正确。正确格式为\"名字#数字\"，例如 BattleTag#1234")
            return
        sender_id = str(event.get_sender_id() or "")
        await self._set_bind(sender_id, tag)
        yield event.plain_result(f"已绑定账号：{tag}\n以后使用 /ow 战绩 等命令无需再输入 BattleTag。")

    @ow.command("解绑")
    async def ow_unbind(self, event: AstrMessageEvent):
        '''解绑你的守望先锋账号'''
        sender_id = str(event.get_sender_id() or "")
        current = await self._get_bind(sender_id)
        if not current:
            yield event.plain_result("你还没有绑定任何账号。")
            return
        await self._remove_bind(sender_id)
        yield event.plain_result(f"已解绑账号：{current}")

    @ow.command("我的绑定")
    async def ow_my_bind(self, event: AstrMessageEvent):
        '''查看当前绑定的守望先锋账号'''
        sender_id = str(event.get_sender_id() or "")
        current = await self._get_bind(sender_id)
        if not current:
            yield event.plain_result(self._no_bind_hint())
            return
        yield event.plain_result(f"当前绑定账号：{current}")

    @ow.command("资料")
    async def ow_profile(self, event: AstrMessageEvent, battletag: str | None = None):
        '''查玩家资料与段位信息'''
        if not self._account_features_ready() or self._profile is None:
            yield event.plain_result(self._account_not_configured_hint())
            return
        tag = await self._resolve_battletag(event, battletag)
        if not tag:
            yield event.plain_result(self._no_bind_hint())
            return
        try:
            from overstats.src.modules.dashen_profile.requests import DashenProfileQuery
            query = DashenProfileQuery(bnet_id=tag)
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_profile", True)
            result = await self._profile.query_profile(query, render=prefer_img)
            lines = [f"玩家：{result.resolved_bnet.full_id if result.resolved_bnet else tag}"]
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                lines.append(f"赛季: {result.bundle.logical_season}")
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 资料查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("战绩")
    async def ow_match(self, event: AstrMessageEvent, battletag: str | int | None = None, limit: int | str | None = None):
        '''查最近战绩列表'''
        if not self._account_features_ready() or self._match is None:
            yield event.plain_result(self._account_not_configured_hint())
            return
        battletag, limit = self._split_optional_battletag_and_number(battletag, limit)
        tag = await self._resolve_battletag(event, battletag)
        if not tag:
            yield event.plain_result(self._no_bind_hint())
            return
        n = limit if limit and 1 <= limit <= 20 else 5
        try:
            from overstats.src.modules.dashen_match.requests import DashenMatchQuery
            query = DashenMatchQuery(bnet_id=tag, target_count=n)
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_match", True)
            if prefer_img:
                await self._ensure_query_tool_assets_ready()
            result = await self._match.query_match_list(query, render=prefer_img)
            lines = [f"玩家：{result.resolved_bnet.full_id if result.resolved_bnet else tag}"]
            lines.append(f"最近 {len(result.matches)} 场战绩：")
            for i, m in enumerate(result.matches):
                result_str = "胜" if m.get("matchRet") == 1 else "败"
                hero = m.get("heroGuid", "?")
                lines.append(f"  {i+1}. {result_str} | 英雄: {hero}")
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 战绩查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("对局详情")
    async def ow_match_detail(self, event: AstrMessageEvent, battletag: str | int | None = None, index: int | str = 1):
        '''查单场对局详细数据'''
        if not self._account_features_ready() or self._match is None:
            yield event.plain_result(self._account_not_configured_hint())
            return
        battletag, parsed_index = self._split_optional_battletag_and_number(battletag, index)
        index = parsed_index or 1
        tag = await self._resolve_battletag(event, battletag)
        if not tag:
            yield event.plain_result(self._no_bind_hint())
            return
        try:
            from overstats.src.modules.dashen_match.requests import DashenMatchQuery
            query = DashenMatchQuery(bnet_id=tag)
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_match_detail", True)
            if prefer_img:
                await self._ensure_query_tool_assets_ready()
            result = await self._match.query_match_detail_by_index(query, index - 1, render=prefer_img)
            detail = result.detail
            lines = [f"对局详情 (第{index}场)"]
            lines.append(f"match_id: {detail.match_id}")
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 对局详情查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("段位")
    async def ow_rank_history(self, event: AstrMessageEvent, battletag: str | None = None):
        '''查段位历史变化'''
        if not self._account_features_ready() or self._rank_history is None:
            yield event.plain_result(self._account_not_configured_hint())
            return
        tag = await self._resolve_battletag(event, battletag)
        if not tag:
            yield event.plain_result(self._no_bind_hint())
            return
        try:
            from overstats.src.modules.dashen_rank_history.requests import DashenRankHistoryQuery
            query = DashenRankHistoryQuery(bnet_id=tag)
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_rank_history", True)
            result = await self._rank_history.query_rank_history(query, render=prefer_img)
            lines = [f"段位历史: {result.resolved_bnet.full_id if result.resolved_bnet else tag}"]
            lines.extend(self._format_rank_history_fallback(list(result.seasons)))
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 段位查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("快速强度")
    async def ow_quick_strength(self, event: AstrMessageEvent, battletag: str | int | None = None, limit: int | str | None = None):
        '''查快速模式强度分析'''
        if not self._account_features_ready() or self._quick_strength is None:
            yield event.plain_result(self._account_not_configured_hint())
            return
        battletag, limit = self._split_optional_battletag_and_number(battletag, limit)
        tag = await self._resolve_battletag(event, battletag)
        if not tag:
            yield event.plain_result(self._no_bind_hint())
            return
        n = limit if limit and 3 <= limit <= 12 else 5
        try:
            from overstats.src.modules.dashen_quick_strength.requests import DashenQuickStrengthQuery
            query = DashenQuickStrengthQuery(bnet_id=tag, limit=n)
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_strength", True)
            result = await self._quick_strength.query_quick_strength(query, render=prefer_img)
            lines = [f"快速强度分析: {result.resolved_bnet.full_id if result.resolved_bnet else tag}"]
            lines.append(f"平均分: {result.summary.overall_avg_score}")
            lines.append(f"段位: {result.summary.overall_avg_rank}")
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 快速强度查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("竞技强度")
    async def ow_competitive_strength(self, event: AstrMessageEvent, battletag: str | int | None = None, limit: int | str | None = None):
        '''查竞技模式强度分析'''
        if not self._account_features_ready() or self._competitive_strength is None:
            yield event.plain_result(self._account_not_configured_hint())
            return
        battletag, limit = self._split_optional_battletag_and_number(battletag, limit)
        tag = await self._resolve_battletag(event, battletag)
        if not tag:
            yield event.plain_result(self._no_bind_hint())
            return
        n = limit if limit and 3 <= limit <= 12 else 5
        try:
            from overstats.src.modules.dashen_competitive_strength.requests import DashenCompetitiveStrengthQuery
            query = DashenCompetitiveStrengthQuery(bnet_id=tag, limit=n)
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_strength", True)
            result = await self._competitive_strength.query_competitive_strength(query, render=prefer_img)
            lines = [f"竞技强度分析: {result.resolved_bnet.full_id if result.resolved_bnet else tag}"]
            lines.append(f"平均分: {result.summary.overall_avg_score}")
            lines.append(f"段位: {result.summary.overall_avg_rank}")
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 竞技强度查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("今日总结")
    async def ow_summary_today(self, event: AstrMessageEvent, battletag: str | None = None):
        '''查今日总结'''
        if not self._account_features_ready() or self._summary is None:
            yield event.plain_result(self._account_not_configured_hint())
            return
        tag = await self._resolve_battletag(event, battletag)
        if not tag:
            yield event.plain_result(self._no_bind_hint())
            return
        try:
            self._sync_summary_runtime_client()
            from overstats.src.modules.dashen_summary.requests import DashenSummaryQuery
            query = DashenSummaryQuery(bnet_id=tag, scope="today")
            result = await self._summary.query_summary(query)
            lines = [f"今日总结: {result.full_id}"]
            lines.append(f"场次: {result.match_count}")
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_summary", True)
            if prefer_img and result.image_bytes:
                from overstats.src.modules.dashen_match.render import RenderedImage
                img = RenderedImage(content=result.image_bytes, media_type=result.image_media_type)
                async for r in self._save_and_send_image(event, img, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 今日总结查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("昨日总结")
    async def ow_summary_yesterday(self, event: AstrMessageEvent, battletag: str | None = None):
        '''查昨日总结'''
        if not self._account_features_ready() or self._summary is None:
            yield event.plain_result(self._account_not_configured_hint())
            return
        tag = await self._resolve_battletag(event, battletag)
        if not tag:
            yield event.plain_result(self._no_bind_hint())
            return
        try:
            self._sync_summary_runtime_client()
            from overstats.src.modules.dashen_summary.requests import DashenSummaryQuery
            query = DashenSummaryQuery(bnet_id=tag, scope="yesterday")
            result = await self._summary.query_summary(query)
            lines = [f"昨日总结: {result.full_id}"]
            lines.append(f"场次: {result.match_count}")
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_summary", True)
            if prefer_img and result.image_bytes:
                from overstats.src.modules.dashen_match.render import RenderedImage
                img = RenderedImage(content=result.image_bytes, media_type=result.image_media_type)
                async for r in self._save_and_send_image(event, img, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 昨日总结查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("本周总结")
    async def ow_summary_week(self, event: AstrMessageEvent, battletag: str | None = None):
        '''查本周总结'''
        if not self._account_features_ready() or self._summary is None:
            yield event.plain_result(self._account_not_configured_hint())
            return
        tag = await self._resolve_battletag(event, battletag)
        if not tag:
            yield event.plain_result(self._no_bind_hint())
            return
        try:
            self._sync_summary_runtime_client()
            from overstats.src.modules.dashen_summary.requests import DashenSummaryQuery
            query = DashenSummaryQuery(bnet_id=tag, scope="week")
            result = await self._summary.query_summary(query)
            lines = [f"本周总结: {result.full_id}"]
            lines.append(f"场次: {result.match_count}")
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_summary", True)
            if prefer_img and result.image_bytes:
                from overstats.src.modules.dashen_match.render import RenderedImage
                img = RenderedImage(content=result.image_bytes, media_type=result.image_media_type)
                async for r in self._save_and_send_image(event, img, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 本周总结查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("英雄热度")
    async def ow_hero_pick_rate_ranking(self, event: AstrMessageEvent, game_mode: str | None = None, mmr: str | None = None):
        '''查英雄选取率榜单'''
        mode = self._cn_mode_to_en(game_mode or "快速")
        rank = self._cn_rank_to_en(mmr or "全部")
        try:
            from overstats.src.modules.ow_hero_pick_rate.service import OWHeroPickRateQuery
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_pick_rate", True)
            if prefer_img:
                await self._ensure_query_tool_assets_ready()
            query = OWHeroPickRateQuery(view="ranking", game_mode=mode, mmr=rank)
            result = await self._pick_rate.query_pick_rate(query, render=prefer_img)
            lines = [f"英雄热度榜单 ({mode} {rank})"]
            if result.heroes:
                for h in result.heroes[:10]:
                    lines.append(
                        f"  {h.rank}. {h.hero_name} 选取率:{h.selection_ratio}% 胜率:{h.win_ratio}%"
                    )
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 英雄热度查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("英雄曲线")
    async def ow_hero_pick_rate_history(self, event: AstrMessageEvent, hero: str, game_mode: str | None = None, mmr: str | None = None):
        '''查单英雄历史选取率曲线'''
        mode = self._cn_mode_to_en(game_mode or "快速")
        rank = self._cn_rank_to_en(mmr or "全部")
        try:
            from overstats.src.modules.ow_hero_pick_rate.service import OWHeroPickRateQuery
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_pick_rate", True)
            if prefer_img:
                await self._ensure_query_tool_assets_ready()
            query = OWHeroPickRateQuery(view="history", game_mode=mode, mmr=rank, hero=hero.strip())
            result = await self._pick_rate.query_pick_rate(query, render=prefer_img)
            lines = [f"英雄选取率曲线: {hero} ({mode} {rank})"]
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 英雄曲线查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("商店")
    async def ow_shop(self, event: AstrMessageEvent):
        '''查守望先锋商店内容'''
        try:
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_shop", True)
            result = await self._shop.query_shop(render=prefer_img)
            lines = ["守望先锋商店"]
            if result.sections:
                for sec in result.sections:
                    title = getattr(sec, 'title', '?')
                    lines.append(f"【{title}】")
                    for item in list(getattr(sec, 'items', []) or [])[:5]:
                        lines.append(f"  {getattr(item, 'title', '?')} - {getattr(item, 'price_raw', '?')} {getattr(item, 'price_currency', '?')}")
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 商店查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("补丁")
    async def ow_patch_notes(self, event: AstrMessageEvent, patch_kind: str | None = None):
        '''查补丁说明'''
        kind = self._cn_patch_kind_to_en(patch_kind or "最新")
        try:
            output_cfg = self.config.get("output", {})
            prefer_img = output_cfg.get("prefer_image_for_patch_notes", True)
            result = await self._patch_notes.query_patch_notes(patch_kind=kind, render=prefer_img)
            lines = [f"补丁说明 ({kind})"]
            if result.selected:
                sel = result.selected
                lines.append(f"标题: {sel.get('title', '?')}")
                lines.append(f"日期: {sel.get('date_text', '?')}")
            if prefer_img and result.image:
                async for r in self._save_and_send_image(event, result.image, "\n".join(lines)):
                    yield r
            else:
                yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 补丁查询失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("搜索玩家")
    async def ow_search_player(self, event: AstrMessageEvent, keyword: str):
        '''搜索不确定的 BattleTag'''
        if self._identity_search is None:
            yield event.plain_result("玩家搜索模块未初始化。")
            return
        try:
            from overstats.src.modules.player_identity_search.service import PlayerIdentitySearchQuery
            query = PlayerIdentitySearchQuery(bnet_id=keyword.strip(), limit=10)
            result = await self._identity_search.search(query)
            lines = [f"搜索 \"{keyword}\" 的结果 ({len(result.matches)} 条)："]
            for m in result.matches:
                lines.append(f"  {m.battletag} (bnet_id: {m.bnet_id})")
            if not result.matches:
                lines.append("  未找到匹配结果")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"[ow_dashen] 搜索玩家失败: {e}")
            yield event.plain_result(f"查询失败：{e}")

    @ow.command("自检")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def ow_self_check(self, event: AstrMessageEvent):
        '''[管理员] 检查大神凭据配置与上游连通性'''
        lines = ["自检结果："]
        try:
            accounts = self.config.get("dashen_accounts", [])
            valid_count = 0
            for acc in accounts:
                enabled = acc.get("enabled", True)
                rid = acc.get("role_id", 0)
                tok = str(acc.get("token") or "").strip()
                if not enabled:
                    lines.append(f"  {acc.get('name', '?')}: 已禁用")
                elif rid == 0 or not tok or "replace-with-your" in tok.lower():
                    lines.append(f"  {acc.get('name', '?')}: role_id 或 token 无效")
                else:
                    valid_count += 1
                    lines.append(f"  {acc.get('name', '?')}: 凭据有效 (role_id={rid})")
            lines.append(f"有效账号数: {valid_count}")
            if self._api_client and valid_count > 0:
                cred = self._api_client.credential_pool.next_credential()
                lines.append(f"当前轮转账号: {cred.name}")
            else:
                lines.append("API 客户端未初始化或无有效账号（首次安装未配置账号属于正常现象）")

            try:
                from overstats.src.modules.query_tool.service import read_query_tool, ensure_query_tool_assets
                query_tool_config = read_query_tool(default={})
                if query_tool_config:
                    asset_result = await asyncio.to_thread(ensure_query_tool_assets, query_tool_config)
                    checked = int(asset_result.get("checked") or 0)
                    cached = int(asset_result.get("cached") or 0)
                    downloaded = int(asset_result.get("downloaded") or 0)
                    failed = int(asset_result.get("failed") or 0)
                    lines.append(
                        "素材缓存: "
                        f"已检查 {checked} 个，已缓存 {cached} 个，新下载 {downloaded} 个，失败 {failed} 个"
                    )
                    if failed:
                        lines.append("素材提示: 有资源下载失败，图片里可能缺英雄头像或地图图。可稍后重试 /ow 自检 或检查网络。")
                else:
                    lines.append("素材缓存: 尚未生成 query_tool.json，首次查询或重载插件后会自动拉取。")
            except Exception as e:
                lines.append(f"素材缓存检查出错: {e}")
        except Exception as e:
            lines.append(f"检查过程出错: {e}")
        yield event.plain_result("\n".join(lines))

    @ow.command("清理缓存")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def ow_cleanup(self, event: AstrMessageEvent):
        '''[管理员] 清理本地图片缓存'''
        removed: list[str] = []
        cache_dirs = [
            _OVERSTATS_DATA_DIR / "cache_img",
            _OVERSTATS_DATA_DIR / "query_tool_assets" / "extra",
            _OVERSTATS_DATA_DIR / "dashen_summary_runtime_cache",
            _TEMP_IMAGE_DIR,
        ]
        try:
            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    removed.append(str(cache_dir))
            if removed:
                yield event.plain_result("已清理以下缓存目录：\n" + "\n".join(f"- {path}" for path in removed))
            else:
                yield event.plain_result("没有检测到可清理的缓存目录")
        except Exception as e:
            yield event.plain_result(f"清理出错: {e}")
