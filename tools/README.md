# 最小输入诊断工具

日常使用云台不需要此工具。仅在你想确认 Android 收到了什么键时运行。

需要 Python 3.9+ 和 [Google 官方 Platform-Tools](https://developer.android.com/tools/releases/platform-tools)。手机通过 USB 连接，在手机上正常开启 USB 调试并授权当前电脑。工具要求恰好一个在线且已授权的设备；多个设备时请先断开其他设备。

```powershell
python tools/input_probe.py --adb "C:\Android\platform-tools\adb.exe" --seconds 60
```

macOS/Linux 或 adb 已加入 PATH：

```sh
python3 tools/input_probe.py --seconds 60
```

等提示 `READY` 后操作一次云台，记录原生相机实际变化。Ctrl+C 提前结束也会保存已收集事件。默认写入 `captures/input-*.json`（已被 .gitignore 排除）。可用 `--output captures/my-test.json` 指定新文件；已有文件不会覆盖。

工具只调用 `adb devices` 和普通 `getevent -lp/-lt`，不修改配对、设置或权限，不执行 root，不写 BLE 数据。它会把输入节点替换为本次运行内的别名，仅输出与本项目有关的控制键及相对时间，不保存原始设备名、序列号、触屏坐标或键盘文字。

如果 getevent 被系统拒绝，脚本会报告失败。**无法读取不能解释为云台没有发送事件。** 即使输出为空，也需核对设备连接、按键时机和采集范围。不同手机的节点编号会变化；`device_1` 只是本轮别名，不等于 OM8。

公开版工具重新整理了原始调试逻辑，只完成离线过滤与错误路径测试，尚未在额外手机上验证；本项目的案例证据来自此前的实机采集，不声称是这份新工具重新采集的结果。
