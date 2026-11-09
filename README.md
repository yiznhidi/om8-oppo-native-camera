# DJI OM8 × OPPO 原生相机

**不用 DJI Mimo 拍摄，保留原生相机，再用云台按键控制。**

一次 Find X9 Ultra 实机排障中，我们在建立配对后，让 OM8 的录像键、变焦拨轮、前后摄像头切换键直接控制了 OPPO 原生相机。最后没有开发桥接 APK，没有 Root，也没有改云台固件。

> **仅在一台 OPPO Find X9 Ultra 上验证。** 这是一份实测经验与诊断工具，不是通用兼容补丁。其他机型、系统版本、固件和拍摄模式请分别验证。

## 已实现什么

| OM8 操作 | 原生相机结果 | 实测 Linux 输入事件 |
| --- | --- | --- |
| 按录像键 | 录像控制成功（用户确认） | `KEY_VOLUMEUP` |
| 旋转侧面拨轮 | 平滑变焦，用户观察到 1× → 8× | `KEY_ZOOMIN` / `KEY_ZOOMOUT` |
| 单击正面的专用切换键 | 前后摄像头切换成功 | `KEY_VIDEO_NEXT` |

专业视频测试环节，用户也确认所选模式可用。不过没有分别记录具体模式名称、LUT、HDR 的开关组合，**不能据此宣称所有高级视频组合均已验证**。

专用切换键位于录像键下方。侧面拨轮向内按压不是本次成功的镜头切换方式；本次未找到其独立按压键值。

## 核心发现：Mimo 能控制，不等于原生相机已有输入通道

最初 Mimo 里可以录像、变焦，原生相机完全无响应。普通 ADB `getevent` 能读输入设备，但按 OM8 时没有对应事件。

后来用户在 Nordic nRF Connect 中对 OM8 执行 **BOND**。随后候选设备显示 **BONDED**，系统新增了名称匹配 OM8 的输入设备。真实按键开始产生上表中的标准事件，原生相机也能响应。

**实测支持：检查系统配对与标准输入通道，值得放在逆向专有协议之前。**

没有执行取消配对→重新配对的对照实验，也没有验证 nRF 退出/卸载后的行为。因此这里只报告时间上关联的成功过程，不保证 BOND 是唯一原因或对所有设备有效。

## 可以尝试的步骤

1. 保持 OM8 开机，手机蓝牙开启。先停止 Mimo，使用原生相机进行独立测试。
2. 从 [Nordic 官方发布页](https://github.com/nordicsemi/Android-nRF-Connect/releases) 安装 **nRF Connect for Mobile**。本次版本为 4.29.1。通过系统弹窗正常授予附近设备等所需权限。
3. 在 **SCANNER** 中扫描，确认条目是你自己的 OM8。不要对周围陌生设备操作。
4. 在该条目的连接选项菜单中选择 **Bond**，按系统提示完成配对。**Bond 与 Connect 是不同操作**；顶部的 **BONDED** 只是标签页，设备条目自身显示 BONDED 才是本次观察到的状态。
5. 保留配对，回到 OPPO 原生相机的普通视频预览。依次验证录像键、拨轮旋转、专用切换键。每次只操作一个控件。
6. 再验证你实际使用的专业视频、LUT 或 HDR 设置。模式是否支持前置镜头、能否在录像中切镜头，由原生相机决定。

本次并没有确认 nRF 的 CONNECT 成功完成了 GATT 服务发现，所以不把它列为成功前提。也不要求写任何 BLE 特征、未知数据或执行固件更新。

如果原生相机只调整音量，可以检查相机自身的音量键用途设置；这属于后续排查建议，本次未靠修改该设置获得成功。

## 验证范围

| 项目 | 本次环境 |
| --- | --- |
| 手机 | OPPO Find X9 Ultra / PMA110 |
| 系统 | ColorOS V17.0.0 / Android 17（API 37） |
| 系统版本 | PMA110_17.0.0.106(CN01) |
| 原生相机 | com.oplus.camera / 7.006.119 |
| 云台 | DJI Osmo Mobile 8；未记录固件版本 |
| Mimo | 2.12.8；成功的录像及变焦独立样本中未运行 |
| nRF Connect | 4.29.1 |
| 测试日期 | 2026-11-09 |

重启重连后的持久性、nRF 是否需要保留、拍照/录像模式切换、全部高级视频组合、录制途中前后切换，尚未逐项验证。其他机型请视为未知，而不是已知不支持。

## 给想复查的人

- [诊断过程与证据边界](docs/diagnosis.md)
- [ADB 输入检查工具](tools/README.md)（Python 标准库，无额外依赖）
- [脱敏案例数据](evidence/find-x9-ultra.json)
- [反馈兼容性](CONTRIBUTING.md)

不需要为了日常使用开启 USB 调试或 HCI 日志；它们只是本次排障工具。若此前开启过 HCI snoop log，完成排障后在开发者选项里关闭。

## English summary

Single-device field report: DJI Osmo Mobile 8 buttons operated the OPPO Find X9 Ultra stock camera after bonding with nRF Connect. Record, smooth zoom, and front/rear camera switching worked without a bridge APK, root, or firmware changes. Standard Linux key events were observed. This is **not a universal compatibility claim**; bonding causality, reconnection persistence, and all LUT/HDR combinations have not been independently established.

## 来源与许可

- [DJI OM8 官方手册](https://dl.djicdn.com/downloads/DJI_Osmo_Mobile_8/UM/20251105/Osmo_Mobile_8_User_Manual_v1.0_en.pdf)：第 12–13 页按钮说明基于 Mimo，原生支持随手机而异。
- [Nordic nRF Connect 官方说明](https://github.com/nordicsemi/Android-nRF-Connect/blob/main/documentation/README.md)：Bond、Connect、服务发现与扫描操作。
- [AOSP getevent 文档](https://source.android.com/docs/core/interaction/input/getevent)；[官方 Platform-Tools](https://developer.android.com/tools/releases/platform-tools)。

社区实测项目，与 DJI、OPPO、Nordic 无隶属关系。原创文档与工具使用 [MIT License](LICENSE)；第三方软件和文档仅链接，不随仓库分发。
