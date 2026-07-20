# 执行器模块 / Actuator Module

全国首个开源机器人执行器 —— 具备高复用性、支持二次开发及规模化部署能力的开源机器人运动驱动架构。

## 模块结构

```
actuator/
├── mechanical/    # 机械结构设计（赵王开源电机项目）
├── pcb/           # 电路板设计
└── software/      # 固件与控制软件
```

## 三部分说明

### 1. mechanical — 机械结构

机械部分引自 **赵王开源电机项目**（Gitee），包含全套机械设计资料：

- 总装配图（STEP 3D 模型）
- 3D 打印件（外壳、减速器、定子内圈、转子等）
- 定子绕线图
- BOM 物料清单

> 项目地址：[https://gitee.com/wlsj_gzw/zhao-wang-open-source](https://gitee.com/wlsj_gzw/zhao-wang-open-source)

### 2. pcb — 线路板

驱动板、电源板、编码器板等硬件电路设计文件。

### 3. software — 软件

执行器控制固件、通信协议、上位机 SDK 等。

## 许可证

本模块衍生作品须遵循 AGPL-3.0 协议保持开源。
机械设计部分遵循其上游项目许可协议。
