# RGB-SOUND CH552 固件

本目录是立创开源项目 `DEEJ-CH552-RGB-Lite` 固件的 RGB-SOUND 修正版。

最终行为：

- 旋钮完全顺时针对应 0%，完全逆时针对应 100%，逆时针旋转时音量增大。
- RGB 音量进度从左往右增加。
- 按钮只向 RGB-SOUND 软件发送静音切换命令，不再切换灯效。
- 灯效由软件设置：关闭、全灯常亮、呼吸灯或全灯同步变色；支持颜色、亮度和速度设置。
- 已移除各灯珠快速异步变化的幻彩/频闪效果。
- 转动旋钮时临时显示对应音量进度，停止 2 秒后恢复所选灯效。

## 直接刷入

预编译文件位于 `RGB-SOUND-CH552.hex`。使用支持 CH552 的烧录工具选择这个文件即可。每次固件源码更新后，GitHub Actions 都会重新编译并更新这个文件。

刷入前必须完全退出 RGB-SOUND，避免串口占用。让板子进入 Bootloader 的方式取决于实际装配版本；本项目原版通常是在重新插入 USB 时按住板载按钮。若设备没有进入 Bootloader，请以原硬件项目的刷机说明为准。

## 从源码编译

使用 Arduino IDE 安装 Ch55xduino 开发板包，打开 `CH552G_4RV_V1.1/CH552G_4RV_V1.1.ino`，选择：

- 开发板：CH552 Board
- Clock Source：16 MHz (internal)
- Upload Method：USB
- USB Settings：USER CODE w/148B USB RAM

然后点击验证或上传。

## 来源与许可

原始固件来自 [DEEJ-CH552-RGB-Lite](https://oshwhub.com/c6c6c6c6c6/deej-ch552-4rv-c6-v1-1)，作者 C6C6C6C6C6，项目标注为 MIT License。本目录保留其代码结构并针对 RGB-SOUND 修改。
