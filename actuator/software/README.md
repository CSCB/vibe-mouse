# 控制软件 / Software

执行器固件与上位机控制软件。

## 规划中的子模块

| 模块 | 说明 | 状态 |
|---|---|---|
| firmware/ | 执行器控制固件（FOC、电流环、位置环） | 待补充 |
| protocol/ | 通信协议定义（CAN / RS485 / UART） | 待补充 |
| sdk/ | 上位机 SDK（Python / C++） | 待补充 |
| tools/ | 调试与校准工具 | 待补充 |

## 目录结构

```
software/
├── firmware/    # 嵌入式固件
├── protocol/    # 通信协议
├── sdk/         # 上位机 SDK
└── tools/       # 调试工具
```
