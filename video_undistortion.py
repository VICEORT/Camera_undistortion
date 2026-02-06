"""
视频畸变矫正程序
读取视频文件，应用相机标定参数进行畸变矫正，并保存矫正后的视频
"""

import cv2
import numpy as np
from scipy.io import loadmat
import sys
import os
from pathlib import Path

def load_camera_params(mat_file_path):
    """
    从MATLAB .mat文件中加载鱼眼相机标定参数
    
    Args:
        mat_file_path: .mat文件路径
    
    Returns:
        camera_matrix: 相机内参矩阵 (3x3)
        dist_coeffs: 畸变系数
        image_size: 图像尺寸
        model: 相机模型类型
        stretch_matrix: 拉伸矩阵 (2x2)
    """
    try:
        # 加载.mat文件，使用struct_as_record=False来正确处理结构体
        mat_data = loadmat(mat_file_path, struct_as_record=False, squeeze_me=True)
        
        print("MAT文件中的所有键:", [k for k in mat_data.keys() if not k.startswith('__')])
        
        if 'camera_data' not in mat_data:
            print("错误: 找不到 'camera_data' 键")
            return None, None, None, None, None
        
        camera_data = mat_data['camera_data']
        
        # 提取参数
        mapping_coeffs = camera_data.mapping_coeffs
        distortion_center = camera_data.distortion_center
        image_size = camera_data.image_size.astype(int)  # [height, width]
        stretch_matrix = camera_data.stretch_matrix
        model = camera_data.model
        
        print(f"\n相机模型: {model}")
        print(f"图像尺寸: {image_size} (高 x 宽)")
        print(f"畸变中心 (主点): {distortion_center}")
        print(f"映射系数: {mapping_coeffs}")
        print(f"拉伸矩阵:\n{stretch_matrix}")
        
        # 第一个系数是焦距
        focal_length = mapping_coeffs[0]
        
        # 构建相机内参矩阵
        camera_matrix = np.array([
            [focal_length, 0, distortion_center[0]],
            [0, focal_length, distortion_center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        # 鱼眼畸变系数: [k1, k2, k3, k4]
        dist_coeffs = np.array([
            mapping_coeffs[1] if len(mapping_coeffs) > 1 else 0.0,
            mapping_coeffs[2] if len(mapping_coeffs) > 2 else 0.0,
            mapping_coeffs[3] if len(mapping_coeffs) > 3 else 0.0,
            0.0
        ], dtype=np.float64)
        
        print("\n相机内参矩阵 (K):")
        print(camera_matrix)
        print("\n鱼眼畸变系数 [k1, k2, k3, k4]:")
        print(dist_coeffs)
        print("\n拉伸矩阵将用于矫正时的旋转变换")
        
        return camera_matrix, dist_coeffs, image_size, model, stretch_matrix
            
    except Exception as e:
        print(f"加载相机参数时出错: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None


def main():
    # 输入输出文件路径
    input_video = r'C:\Users\HP\Downloads\my_video-2.mkv'  # 输入视频路径
    output_video = r'D:\RM\FSEYE\my_video-2_undistorted.mp4'  # 输出视频路径
    
    # 加载相机标定参数
    mat_file = r'D:\RM\FSEYE\camera_params_final.mat'
    print(f"正在加载相机参数: {mat_file}")
    
    camera_matrix, dist_coeffs, cal_image_size, model, stretch_matrix = load_camera_params(mat_file)
    
    if camera_matrix is None:
        print("无法加载相机参数，程序退出")
        sys.exit(1)
    
    # 检查输入视频是否存在
    if not os.path.exists(input_video):
        print(f"\n错误: 输入视频文件不存在: {input_video}")
        print("请修改程序中的 input_video 路径")
        sys.exit(1)
    
    # 打开输入视频
    print(f"\n正在打开视频文件: {input_video}")
    cap = cv2.VideoCapture(input_video)
    
    if not cap.isOpened():
        print(f"错误: 无法打开视频文件: {input_video}")
        sys.exit(1)
    
    # 获取视频属性
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"视频信息:")
    print(f"  分辨率: {width}x{height}")
    print(f"  帧率: {fps} fps")
    print(f"  总帧数: {total_frames}")
    print(f"  时长: {total_frames/fps:.2f} 秒")
    
    # 检查视频分辨率是否与标定分辨率匹配
    if width != cal_image_size[1] or height != cal_image_size[0]:
        print(f"\n警告: 视频分辨率({width}x{height})与标定分辨率({cal_image_size[1]}x{cal_image_size[0]})不匹配！")
        print("将自动调整相机参数以匹配视频分辨率")
    
    # 准备畸变矫正映射
    is_fisheye = (model.lower() == 'fisheye')
    
    if is_fisheye:
        print("\n使用鱼眼相机畸变矫正模型")
        
        # 调整相机内参矩阵以匹配实际分辨率
        if width != cal_image_size[1] or height != cal_image_size[0]:
            scale_x = width / cal_image_size[1]
            scale_y = height / cal_image_size[0]
            scaled_camera_matrix = camera_matrix.copy()
            scaled_camera_matrix[0, 0] *= scale_x  # fx
            scaled_camera_matrix[1, 1] *= scale_y  # fy
            scaled_camera_matrix[0, 2] *= scale_x  # cx
            scaled_camera_matrix[1, 2] *= scale_y  # cy
            print(f"缩放相机内参矩阵: scale_x={scale_x:.3f}, scale_y={scale_y:.3f}")
        else:
            scaled_camera_matrix = camera_matrix
        
        # 构建3x3的旋转矩阵，结合StretchMatrix
        R = np.eye(3, dtype=np.float64)
        R[0:2, 0:2] = stretch_matrix
        
        # 使用原始相机矩阵作为新相机矩阵
        new_camera_matrix = scaled_camera_matrix.copy()
        
        print("计算畸变矫正映射...")
        # 计算畸变矫正映射
        map1, map2 = cv2.fisheye.initUndistortRectifyMap(
            scaled_camera_matrix, dist_coeffs, R, new_camera_matrix,
            (width, height), cv2.CV_16SC2)
    else:
        print("\n使用标准相机畸变矫正模型")
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            camera_matrix, dist_coeffs[:5], (width, height), 1, (width, height))
        
        print("计算畸变矫正映射...")
        map1, map2 = cv2.initUndistortRectifyMap(
            camera_matrix, dist_coeffs[:5], None, new_camera_matrix,
            (width, height), cv2.CV_16SC2)
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 使用MP4编码
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"错误: 无法创建输出视频文件: {output_video}")
        cap.release()
        sys.exit(1)
    
    print(f"\n开始处理视频...")
    print(f"输出文件: {output_video}")
    print("处理进度:")
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            break
        
        # 应用畸变矫正
        undistorted = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)
        
        # 写入输出视频
        out.write(undistorted)
        
        frame_count += 1
        
        # 显示进度
        if frame_count % 30 == 0 or frame_count == total_frames:
            progress = (frame_count / total_frames) * 100
            print(f"  进度: {frame_count}/{total_frames} 帧 ({progress:.1f}%)")
        
        # 可选：显示预览（按q退出）
        if frame_count % 5 == 0:  # 每5帧显示一次以提高性能
            preview = cv2.resize(undistorted, (960, 540))  # 缩小预览
            cv2.putText(preview, f'Processing: {frame_count}/{total_frames}', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Video Undistortion Preview (Press q to cancel)', preview)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n用户取消处理")
                break
    
    # 释放资源
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    if frame_count == total_frames:
        print(f"\n✓ 视频处理完成！")
        print(f"  处理帧数: {frame_count}")
        print(f"  输出文件: {output_video}")
        
        # 检查输出文件大小
        if os.path.exists(output_video):
            file_size = os.path.getsize(output_video) / (1024 * 1024)  # MB
            print(f"  文件大小: {file_size:.2f} MB")
    else:
        print(f"\n! 处理提前终止")
        print(f"  已处理帧数: {frame_count}/{total_frames}")


if __name__ == '__main__':
    main()
