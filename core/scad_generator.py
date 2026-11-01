"""
OpenSCAD 模型生成器 / OpenSCAD Model Generator

将大模型生成的 OpenSCAD 代码保存为 .scad 文件，并调用本机 OpenSCAD CLI
渲染生成 .stl 文件（3D 打印可直接导入切片软件，如 Bambu Studio）。

输出目录：项目根目录 / output /（自动创建，无需手动建立）

依赖：本机已安装 OpenSCAD（https://openscad.org）
  - Windows 常见安装路径：C:\\Program Files\\OpenSCAD\\openscad.exe
  - 也可将 openscad 加入 PATH
"""

import os
import re
import shutil
import platform
import datetime
import subprocess
from typing import Optional, Tuple


class ScadGenerator:
    """OpenSCAD 参数化建模生成器：自然语言 → SCAD 代码 → STL 文件"""

    # Windows 常见 OpenSCAD 安装路径
    _WINDOWS_CANDIDATES = [
        r"C:\Program Files\OpenSCAD\openscad.exe",
        r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
    ]

    # macOS 默认安装路径
    _MACOS_PATH = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(project_root, "output")
        self.output_dir = output_dir

    # ------------------------------------------------------------------
    # 可执行文件查找
    # ------------------------------------------------------------------
    def find_openscad(self) -> Optional[str]:
        """查找 OpenSCAD 可执行文件路径"""
        # 1. 从 PATH 查找（Linux/macOS 常见；Windows 手动加入 PATH 后亦可）
        exe = shutil.which("openscad") or shutil.which("openscad.exe")
        if exe:
            return exe

        system = platform.system()
        # 2. Windows 常见安装路径
        if system == "Windows":
            for p in self._WINDOWS_CANDIDATES:
                if os.path.exists(p):
                    return p
        # 3. macOS 默认安装路径
        elif system == "Darwin" and os.path.exists(self._MACOS_PATH):
            return self._MACOS_PATH

        return None

    # ------------------------------------------------------------------
    # SCAD 代码清理
    # ------------------------------------------------------------------
    @staticmethod
    def extract_scad_code(text: str) -> str:
        """从模型回复中提取纯 OpenSCAD 代码（去除 Markdown 代码块等杂质）"""
        if not text:
            return ""
        text = text.strip()
        # 去除 Markdown 代码块围栏（```scad / ```openscad / ```）
        text = re.sub(r"```(?:scad|openscad)?", "", text, flags=re.IGNORECASE)
        text = text.replace("```", "")
        return text.strip()

    # ------------------------------------------------------------------
    # 主入口：生成 STL
    # ------------------------------------------------------------------
    def generate(self, scad_code: str, name: Optional[str] = None) -> Tuple[bool, str]:
        """
        保存 .scad 并渲染生成 .stl。

        Args:
            scad_code: 模型生成的 OpenSCAD 代码（可能带 Markdown 围栏）
            name: 输出文件名（不含扩展名）。缺省用时间戳自动命名。

        Returns:
            (success, message)
              - success=True 时 message 为生成的 STL 文件绝对路径
              - success=False 时 message 为错误说明
        """
        code = self.extract_scad_code(scad_code)
        if not code:
            return False, "未能从模型回复中提取 OpenSCAD 代码"

        openscad = self.find_openscad()
        if not openscad:
            return False, (
                "未检测到 OpenSCAD，请先安装并加入 PATH：https://openscad.org"
            )

        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            return False, f"无法创建输出目录 {self.output_dir}: {e}"

        if name is None:
            name = "scad_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # 文件名清洗，避免路径注入
        name = re.sub(r"[^\w\-]+", "_", name)

        scad_path = os.path.join(self.output_dir, name + ".scad")
        stl_path = os.path.join(self.output_dir, name + ".stl")

        try:
            with open(scad_path, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as e:
            return False, f"写入 .scad 文件失败: {e}"

        print(f"[ScadGenerator] 已保存 SCAD: {scad_path}")
        print(f"[ScadGenerator] OpenSCAD: {openscad}")

        try:
            result = subprocess.run(
                [openscad, "-o", stl_path, scad_path],
                capture_output=True,
                text=True,
                timeout=300,  # 复杂模型渲染可能较慢
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return False, "OpenSCAD 渲染超时（>5 分钟），请简化模型参数"
        except Exception as e:
            return False, f"调用 OpenSCAD 失败: {e}"

        if result.returncode != 0 or not os.path.exists(stl_path):
            err = (result.stderr or result.stdout or "").strip()
            return False, f"OpenSCAD 渲染失败: {err[:300] if err else '未知错误'}"

        print(f"[ScadGenerator] 已生成 STL: {stl_path}")
        return True, stl_path
