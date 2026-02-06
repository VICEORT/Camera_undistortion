# FSEYE - 鱼眼相机畸变矫正工具

一个基于OpenCV的鱼眼相机实时畸变矫正和视频处理工具，支持从MATLAB标定参数中自动加载相机参数。

## 功能特性

- ✅ **实时相机畸变矫正**：支持USB相机实时画面矫正，帧率可达90fps
- ✅ **视频批量处理**：对录制的视频文件进行畸变矫正，支持多种视频格式
- ✅ **鱼眼相机支持**：专门优化的鱼眼相机畸变模型
- ✅ **完整画面输出**：矫正后保持完整分辨率，无裁剪
- ✅ **MATLAB参数兼容**：直接读取MATLAB Camera Calibrator导出的.mat参数文件
- ✅ **拉伸矫正**：支持StretchMatrix校正图像拉伸变形

## 系统要求

- Python 3.7+
- Windows / Linux / macOS
- USB相机（支持DirectShow）

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/你的用户名/FSEYE.git
cd FSEYE
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install opencv-python scipy numpy
```

## 使用方法

### 实时相机畸变矫正

用于实时预览相机画面并应用畸变矫正：

```bash
python camera_undistortion.py
```

**操作说明：**
- `q` - 退出程序
- `s` - 保存当前矫正后的图像
- `c` - 切换显示模式（对比/仅矫正）
- `o` - 查看原始图像（无矫正）
- `d` - 显示调试信息

**相机设置：**
- 分辨率：1920x1080
- 帧率：90 fps
- 自动检测USB相机

### 视频文件畸变矫正

对已录制的视频文件进行批量矫正：

```bash
python video_undistortion.py
```

**修改输入文件：**

编辑 `video_undistortion.py` 第87行：

```python
input_video = r'C:\path\to\your\video.mkv'  # 修改为你的视频路径
```

程序会自动：
- 读取视频并应用畸变矫正
- 显示处理进度
- 保存矫正后的视频为 MP4 格式
- 提供实时预览窗口

## 相机标定参数

程序使用MATLAB Camera Calibrator导出的`.mat`文件作为标定参数。参数文件结构：

```matlab
camera_data:
  - MappingCoefficients: [fx, k1, k2, k3]  % 焦距和畸变系数
  - DistortionCenter: [cx, cy]             % 主点坐标
  - ImageSize: [height, width]             % 图像尺寸
  - StretchMatrix: [2x2 matrix]            % 拉伸校正矩阵
  - Model: 'fisheye'                       % 相机模型类型
```

### 如何生成标定参数

1. 在MATLAB中使用 **Camera Calibrator App**
2. 使用棋盘格标定板采集多张图像
3. 完成标定后，导出参数
4. 将 `cameraParams` 保存为 `.mat` 文件

**示例MATLAB代码：**

```matlab
% 保存标定参数
camera_data.mapping_coeffs = [cameraParams.Intrinsics.K(1,1), ...
    cameraParams.Intrinsics.RadialDistortion];
camera_data.distortion_center = cameraParams.Intrinsics.PrincipalPoint;
camera_data.image_size = cameraParams.Intrinsics.ImageSize;
camera_data.stretch_matrix = eye(2);  % 或使用实际的拉伸矩阵
camera_data.model = 'fisheye';

save('camera_params_final.mat', 'camera_data');
```

## 工具脚本

### inspect_mat.py

检查`.mat`文件内容的实用工具：

```bash
python inspect_mat.py
```

输出所有相机参数的详细信息，用于调试和验证参数文件。

## 项目结构

```
FSEYE/
├── camera_undistortion.py      # 实时相机畸变矫正
├── video_undistortion.py       # 视频文件畸变矫正
├── inspect_mat.py              # MAT文件检查工具
├── camera_params_final.mat     # 相机标定参数文件
├── requirements.txt            # Python依赖
└── README.md                   # 项目文档
```

## 技术细节

### 畸变矫正原理

1. **加载相机参数**：从MATLAB `.mat`文件读取内参矩阵、畸变系数和拉伸矩阵
2. **计算映射表**：使用OpenCV的 `cv2.fisheye.initUndistortRectifyMap()` 预计算像素映射
3. **实时重映射**：使用 `cv2.remap()` 对每一帧应用畸变矫正
4. **拉伸校正**：通过旋转矩阵R应用StretchMatrix变换

### 性能优化

- 预计算畸变映射表（一次计算，重复使用）
- 使用 `cv2.CV_16SC2` 格式的映射表以提高速度
- DirectShow后端提供更好的相机控制
- 视频处理支持实时预览但不影响处理速度

## 常见问题

### Q: 矫正后的画面是黑色的？

**A:** 检查以下几点：
- 确认相机分辨率与标定分辨率匹配（1920x1080）
- 查看调试图像 `debug_undistorted.jpg` 确认是否有内容
- 尝试调整 `balance` 参数（在代码中）

### Q: 无法检测到USB相机？

**A:** 
- 确保USB相机已正确连接
- 程序会自动列出所有可用相机，选择正确的索引
- Windows用户可能需要安装相机驱动

### Q: 视频处理速度慢？

**A:** 
- 关闭预览窗口可以提高处理速度
- 考虑使用GPU加速版本的OpenCV
- 减少视频分辨率或采样率

### Q: 相机帧率无法达到90fps？

**A:** 
- 确认相机硬件支持90fps
- 检查USB接口速度（建议USB 3.0+）
- 关闭不必要的后台程序释放CPU资源

## 示例输出

### 实时相机矫正
![Real-time Undistortion](https://via.placeholder.com/800x450?text=Real-time+Camera+Undistortion)

### 视频处理进度
```
处理进度:
  进度: 1500/3865 帧 (38.8%)
  进度: 1800/3865 帧 (46.6%)
  进度: 2100/3865 帧 (54.3%)
  ...
✓ 视频处理完成！
  处理帧数: 3865
  输出文件: D:\RM\FSEYE\my_video_undistorted.mp4
  文件大小: 245.67 MB
```

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 作者

东南大学3SE战队蒲柏均 - 计算机视觉项目

## 致谢

- OpenCV团队提供的优秀计算机视觉库
- MATLAB Camera Calibrator工具
- 所有贡献者和用户

---

**如果这个项目对你有帮助，请给个⭐Star支持一下！**
