"""
工具切换器 / Tool Switcher

管理工具切换时的历史状态快照，实现：
- 切换工具时自动保存当前状态（Skill、覆盖层等）
- 切回工具时自动恢复之前的状态
- 维护工具使用历史记录
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


class SwitchReason(Enum):
    """切换原因"""
    MANUAL = "manual"          # 手动切换
    AUTO_DETECT = "auto"       # 自动检测切换
    SKILL_TRIGGER = "skill"    # Skill 触发切换
    COMMAND_LINE = "cli"       # 命令行切换


@dataclass
class ToolSnapshot:
    """工具状态快照"""
    tool_name: str
    active_skill: Optional[str] = None           # 激活的 Skill 名称
    skill_context: dict = field(default_factory=dict)
    shortcut_overrides: dict = field(default_factory=dict)
    feedback_override: dict = field(default_factory=dict)
    device_overrides: list = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "active_skill": self.active_skill,
            "skill_context": self.skill_context,
            "shortcut_overrides": self.shortcut_overrides,
            "feedback_override": self.feedback_override,
            "device_overrides": self.device_overrides,
            "timestamp": self.timestamp,
        }


@dataclass
class SwitchRecord:
    """切换记录"""
    from_tool: Optional[str]
    to_tool: str
    reason: SwitchReason
    timestamp: float = field(default_factory=time.time)
    snapshot: Optional[ToolSnapshot] = None


class ToolSwitcher:
    """
    工具切换器

    负责：
    1. 保存/恢复每个工具的状态快照
    2. 记录切换历史
    3. 提供便捷的切换接口
    """

    def __init__(self, config, executor):
        self.config = config
        self.executor = executor
        self._snapshots: Dict[str, ToolSnapshot] = {}    # tool_name -> snapshot
        self._history: List[SwitchRecord] = []            # 切换历史记录
        self._max_history = 50                            # 最大历史记录数

    def switch(self, target_tool: str, reason: SwitchReason = SwitchReason.MANUAL):
        """
        切换到指定工具，自动保存/恢复状态

        Args:
            target_tool: 目标工具名
            reason: 切换原因
        """
        current_tool = self.config.current_tool

        if current_tool == target_tool:
            return

        print(f"[ToolSwitcher] 切换工具: {current_tool} -> {target_tool} (reason={reason.value})")

        # 1. 保存当前工具状态
        self._save_snapshot(current_tool)

        # 2. 执行工具切换
        self.executor.switch_tool(target_tool)

        # 3. 恢复目标工具的历史状态
        self._restore_snapshot(target_tool)

        # 4. 记录切换历史
        record = SwitchRecord(
            from_tool=current_tool,
            to_tool=target_tool,
            reason=reason,
            snapshot=self._snapshots.get(current_tool)
        )
        self._history.append(record)
        self._trim_history()

    def _save_snapshot(self, tool_name: str):
        """保存指定工具的当前状态"""
        snapshot = ToolSnapshot(tool_name=tool_name)

        # 保存当前激活的 Skill
        if self.executor.active_skill:
            snapshot.active_skill = self.executor.active_skill.name
            snapshot.skill_context = dict(self.executor.active_skill_context)

        # 保存配置覆盖层
        snapshot.shortcut_overrides = dict(self.config._skill_shortcut_override)
        snapshot.feedback_override = dict(self.config._skill_feedback_override)
        snapshot.device_overrides = list(self.config._skill_device_overrides)

        self._snapshots[tool_name] = snapshot
        print(f"[ToolSwitcher] 已保存快照: {tool_name} (skill={snapshot.active_skill})")

    def _restore_snapshot(self, tool_name: str):
        """恢复指定工具的历史状态"""
        snapshot = self._snapshots.get(tool_name)
        if not snapshot:
            print(f"[ToolSwitcher] 无历史快照: {tool_name}，使用默认配置")
            # 确保清除任何遗留的覆盖
            self.config.clear_skill_overrides()
            if hasattr(self.executor.feedback, 'update_config'):
                self.executor.feedback.update_config(self.config.get_base_feedback())
            return

        # 恢复 Skill
        if snapshot.active_skill and self.executor.skill_engine:
            skill = self.executor.skill_engine.skills.get(snapshot.active_skill)
            if skill and skill.enabled:
                print(f"[ToolSwitcher] 恢复 Skill: {snapshot.active_skill}")
                # 重新激活 Skill（会应用覆盖层）
                self.executor._execute_skill(f"skill:{snapshot.active_skill}")
            else:
                print(f"[ToolSwitcher] Skill 已不可用: {snapshot.active_skill}")
        else:
            # 无 Skill 激活，清除覆盖
            self.config.clear_skill_overrides()
            if hasattr(self.executor.feedback, 'update_config'):
                self.executor.feedback.update_config(self.config.get_base_feedback())

        print(f"[ToolSwitcher] 已恢复快照: {tool_name}")

    def _trim_history(self):
        """裁剪历史记录"""
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(self, limit: int = 10) -> List[SwitchRecord]:
        """获取最近的切换历史"""
        return self._history[-limit:]

    def get_history_summary(self) -> List[dict]:
        """获取历史摘要（用于 UI 显示）"""
        return [
            {
                "from": r.from_tool or "-",
                "to": r.to_tool,
                "reason": r.reason.value,
                "time": time.strftime("%H:%M:%S", time.localtime(r.timestamp)),
                "skill": r.snapshot.active_skill if r.snapshot else None,
            }
            for r in self._history
        ]

    def get_most_used_tools(self) -> Dict[str, int]:
        """获取使用频率统计"""
        counts = {}
        for record in self._history:
            counts[record.to_tool] = counts.get(record.to_tool, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def clear_history(self):
        """清空历史记录"""
        self._history.clear()
        self._snapshots.clear()
        print("[ToolSwitcher] 历史记录已清空")

    def quick_switch(self):
        """快速切换到上一个工具"""
        if len(self._history) < 1:
            print("[ToolSwitcher] 无切换历史")
            return

        # 找到最近一次切换的源工具
        last_record = self._history[-1]
        if last_record.from_tool:
            self.switch(last_record.from_tool, SwitchReason.MANUAL)
