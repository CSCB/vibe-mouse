import threading
import time
import psutil

class CompletionDetector:
    """
    基于进程 IO 的完成检测器。
    Trae/Cursor 是基于 Electron 的应用，AI 生成期间会产生大量的网络接收和磁盘写入。
    通过汇总目标 IDE 所有子进程的 io_counters (包含网络和磁盘 IO)，
    我们可以非常精准地判断 AI 是处于流式输出中 (高 IO)，还是已经完成 (低 IO)。
    无需管理员权限即可运行。
    """
    def __init__(self, config, on_start_callback, on_done_callback):
        self.config = config
        self.on_start_callback = on_start_callback
        self.on_done_callback = on_done_callback
        self.is_detecting = False
        self._thread = None
        self._reset_requested = False

    def _get_target_process_names(self):
        tool = self.config.current_tool.lower()
        # 返回进程名前缀列表（精确名或前缀均可，见 _get_total_io）
        if "trae" in tool: return ["trae"]
        if "cursor" in tool: return ["cursor"]
        if "windsurf" in tool: return ["windsurf"]
        if "copilot" in tool: return ["code.exe"]  # VS Code 主进程（前缀避免误匹配 codearts 等）
        if "deveco_studio" in tool: return ["devecostudio"]
        if "deveco_code" in tool: return ["devecocode"]
        # CodeArts：主进程 codearts-agent.exe，AI 内核 AgentKernel_Vscode_<版本>.exe
        if "codearts" in tool: return ["codearts", "agentkernel_vscode"]
        return []

    def reset_state(self):
        """请求重置检测状态（切换工具时调用，避免旧工具的 IO 基线干扰）"""
        self._reset_requested = True

    def _get_total_io(self, proc_names):
        total_io = 0
        for p in psutil.process_iter(['name', 'io_counters']):
            try:
                name = (p.info.get('name') or '').lower()
                # 精确名或前缀匹配（如 "codearts" 匹配 codearts-agent.exe，
                # "agentkernel_vscode" 匹配 AgentKernel_Vscode_<版本>.exe）
                if name and any(name == pn or name.startswith(pn) for pn in proc_names):
                    io = p.info.get('io_counters')
                    if io:
                        total_io += getattr(io, 'read_bytes', 0) + getattr(io, 'write_bytes', 0)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return total_io

    def start_detecting(self):
        if self.is_detecting:
            return

        self.is_detecting = True
        self._thread = threading.Thread(target=self._detect_loop, daemon=True)
        self._thread.start()

    def stop_detecting(self):
        self.is_detecting = False

    def _detect_loop(self):
        # 阈值设置 (字节)
        spike_threshold = 1024 * 500  # 判定为开始生成的阈值：0.5秒内产生 >500KB IO
        drop_threshold = 1024 * 10    # 判定为生成停止的固定下限：0.5秒内产生 <10KB IO
        interval = 0.5                # 轮询间隔 0.5 秒

        state = "WAITING_SPIKE"
        drop_count = 0
        spike_count = 0
        last_io = 0
        idle_baseline = 0.0  # 空闲 IO 基线（EMA）。codearts-agent 等后台进程空闲时也有持续 IO，
                             # 固定跌落阈值会永远等不到跌落，故用 max(固定阈值, 3×基线) 自适应

        print("[Detector] 后台全局 IO 监听服务已启动 / Global IO monitoring daemon started...")

        while self.is_detecting:
            time.sleep(interval)

            # 切换工具时重置状态
            if self._reset_requested:
                state = "WAITING_SPIKE"
                drop_count = 0
                spike_count = 0
                last_io = 0
                idle_baseline = 0.0
                self._reset_requested = False
                print(f"[Detector] 检测状态已重置，当前工具: {self.config.current_tool}")
                continue

            proc_names = self._get_target_process_names()
            if not proc_names:
                continue

            current_io = self._get_total_io(proc_names)

            # 初始化 last_io（首次或切换工具后）
            if last_io == 0:
                last_io = current_io
                continue

            delta = current_io - last_io
            last_io = current_io

            if state == "WAITING_SPIKE":
                if delta > spike_threshold:
                    spike_count += 1
                    # 连续 3 个尖峰（1.5 秒持续高 IO）才判定开始，
                    # 过滤后台进程偶发的 2 连突发（如启动索引）
                    if spike_count >= 3:
                        print(f"\n[Detector] 连续捕捉到巨大 IO ({delta} bytes)！判定 AI 开始真实工作...")
                        state = "WAITING_DROP"
                        spike_count = 0
                        if self.on_start_callback:
                            self.on_start_callback()
                else:
                    spike_count = 0
                    # 非尖峰期更新空闲基线（指数滑动平均）。
                    # 负 delta（CodeArts 等后台子进程退出导致累计 IO 回退）不参与计算，
                    # 否则基线可能被污染为负值，跌落阈值退化为固定 10KB，完成判定永远不触发
                    if delta > 0:
                        idle_baseline = delta if idle_baseline <= 0 else idle_baseline * 0.9 + delta * 0.1

            elif state == "WAITING_DROP":
                # 自适应跌落阈值：固定下限与空闲基线 3 倍取大
                effective_drop = max(drop_threshold, idle_baseline * 3)
                if delta <= effective_drop:
                    drop_count += 1
                    print(f"[Detector] 流量跌落判定中... ({drop_count}/6) - 当前 IO: {delta} (阈值 {int(effective_drop)})")
                    if drop_count >= 6:
                        print(f"[Detector] 连续 3 秒低 IO，判定生成彻底完毕！重置状态...")
                        state = "WAITING_SPIKE"
                        drop_count = 0
                        if self.on_done_callback:
                            self.on_done_callback()
                else:
                    if drop_count > 0:
                        print(f"[Detector] 流量回升 ({delta} bytes)，打断跌落判定！")
                    drop_count = 0
