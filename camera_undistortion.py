"""
USB相机实时畸变矫正程序（鱼眼相机版本）
读取MATLAB标定参数并实时矫正相机画面
"""

import cv2
import numpy as np
from scipy.io import loadmat
import sys

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
        # K = [[fx, 0, cx],
        #      [0, fy, cy],
        #      [0,  0,  1]]
        camera_matrix = np.array([
            [focal_length, 0, distortion_center[0]],
            [0, focal_length, distortion_center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        # 鱼眼畸变系数: [k1, k2, k3, k4]
        # 从mapping_coeffs中提取（跳过第一个焦距参数）
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
    # 加载相机标定参数
    mat_file = r'D:\RM\FSEYE\camera_params_final.mat'
    print(f"正在加载相机参数: {mat_file}")
    
    camera_matrix, dist_coeffs, cal_image_size, model, stretch_matrix = load_camera_params(mat_file)
    
    if camera_matrix is None:
        print("无法加载相机参数，程序退出")
        sys.exit(1)
    
    # 检测所有可用的相机
    print("\n正在检测所有可用的相机...")
    available_cameras = []
    for i in range(10):  # 检测前10个相机索引
        cap_test = cv2.VideoCapture(i)
        if cap_test.isOpened():
            ret, frame = cap_test.read()
            if ret:
                width = int(cap_test.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap_test.get(cv2.CAP_PROP_FRAME_HEIGHT))
                available_cameras.append((i, width, height))
                print(f"  相机 {i}: {width}x{height}")
            cap_test.release()
    
    if not available_cameras:
        print("错误: 未检测到任何相机")
        sys.exit(1)
    
    # 选择相机
    if len(available_cameras) == 1:
        camera_index = available_cameras[0][0]
        print(f"\n只检测到一个相机，使用相机 {camera_index}")
    else:
        print(f"\n检测到 {len(available_cameras)} 个相机")
        # 优先选择分辨率最接近标定分辨率的相机
        best_match = None
        min_diff = float('inf')
        for idx, w, h in available_cameras:
            diff = abs(w - cal_image_size[1]) + abs(h - cal_image_size[0])
            if diff < min_diff:
                min_diff = diff
                best_match = idx
        
        # 如果最佳匹配是相机0且有其他选项，询问用户
        if best_match == 0 and len(available_cameras) > 1:
            print(f"建议使用相机 {available_cameras[1][0]} (USB相机通常是索引1或更高)")
            user_input = input(f"请输入要使用的相机编号 (0-{len(available_cameras)-1})，或直接回车使用相机 {available_cameras[1][0]}: ")
            if user_input.strip():
                try:
                    selected = int(user_input.strip())
                    camera_index = available_cameras[selected][0]
                except:
                    camera_index = available_cameras[1][0]
            else:
                camera_index = available_cameras[1][0]
        else:
            camera_index = best_match
    
    print(f"\n正在打开相机 {camera_index}...")
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)  # 使用DirectShow后端以获得更好的控制
    
    if not cap.isOpened():
        print(f"错误: 无法打开相机 {camera_index}")
        sys.exit(1)
    
    # 设置相机分辨率为1920x1080
    print("\n设置相机参数...")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 90)  # 设置帧率为90fps
    
    # 获取实际设置的相机画面尺寸
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"相机分辨率: {width}x{height} @ {fps}fps")
    print(f"标定图像尺寸: {cal_image_size[1]}x{cal_image_size[0]} (宽x高)")
    
    # 如果相机分辨率与标定时不同，给出警告
    if width != cal_image_size[1] or height != cal_image_size[0]:
        print(f"\n警告: 相机分辨率({width}x{height})与标定分辨率({cal_image_size[1]}x{cal_image_size[0]})不匹配！")
        print("矫正效果可能不理想，建议调整相机分辨率或重新标定。")
    
    # 对于鱼眼相机，使用 cv2.fisheye 模块
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
        # StretchMatrix是2x2，需要扩展为3x3
        R = np.eye(3, dtype=np.float64)
        R[0:2, 0:2] = stretch_matrix
        
        print("\n拉伸矩阵 (2x2):")
        print(stretch_matrix)
        print("\n旋转矩阵 R (3x3)，包含拉伸变换:")
        print(R)
        
        # 对于鱼眼相机，直接使用原始相机矩阵作为新相机矩阵
        # 这样可以保持焦距和主点不变
        new_camera_matrix = scaled_camera_matrix.copy()
        
        print("\n缩放后的相机内参矩阵:")
        print(scaled_camera_matrix)
        print(f"\n新的相机内参矩阵 (与原矩阵相同):")
        print(new_camera_matrix)
        
        # 计算畸变矫正映射，使用R矩阵应用拉伸变换
        try:
            map1, map2 = cv2.fisheye.initUndistortRectifyMap(
                scaled_camera_matrix, dist_coeffs, R, new_camera_matrix,
                (width, height), cv2.CV_16SC2)
        except Exception as e:
            print(f"鱼眼映射计算失败: {e}")
            print("尝试使用标准畸变矫正模型...")
            is_fisheye = False
    else:
        print("\n使用标准相机畸变矫正模型")
        # 标准相机模型
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            camera_matrix, dist_coeffs[:5], (width, height), 1, (width, height))
        
        # 计算畸变矫正映射
        map1, map2 = cv2.initUndistortRectifyMap(
            camera_matrix, dist_coeffs[:5], None, new_camera_matrix,
            (width, height), cv2.CV_16SC2)
    
    print("\n相机已就绪，开始实时矫正...")
    print("按 'q' 键退出")
    print("按 's' 键保存当前矫正后的图像")
    print("按 'c' 键切换显示模式（对比/仅矫正）")
    print("按 'o' 键查看原始图像（无矫正）")
    print("按 'd' 键显示调试信息")
    
    frame_count = 0
    show_comparison = False  # 默认只显示矫正后的画面
    show_debug = False
    
    # 读取第一帧进行测试
    ret, test_frame = cap.read()
    if ret:
        print(f"\n第一帧图像信息:")
        print(f"  形状: {test_frame.shape}")
        print(f"  类型: {test_frame.dtype}")
        print(f"  范围: [{test_frame.min()}, {test_frame.max()}]")
        
        # 测试矫正
        test_undistorted = cv2.remap(test_frame, map1, map2, cv2.INTER_LINEAR)
        print(f"矫正后图像信息:")
        print(f"  形状: {test_undistorted.shape}")
        print(f"  类型: {test_undistorted.dtype}")
        print(f"  范围: [{test_undistorted.min()}, {test_undistorted.max()}]")
        
        # 保存第一帧用于调试
        cv2.imwrite('debug_original.jpg', test_frame)
        cv2.imwrite('debug_undistorted.jpg', test_undistorted)
        print("已保存调试图像: debug_original.jpg, debug_undistorted.jpg")
    
    while True:
        # 读取一帧
        ret, frame = cap.read()
        
        if not ret:
            print("无法读取相机画面")
            break
        
        # 使用预计算的映射进行畸变矫正（这种方法更快）
        undistorted = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)
        
        # 在图像上添加文字标签
        frame_count += 1
        
        if show_comparison:
            # 并排显示原始和矫正后的图像
            cv2.putText(frame, 'Original', (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(undistorted, 'Undistorted', (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 调整大小以适应屏幕
            scale = 0.5 if width > 1280 else 1.0
            if scale != 1.0:
                frame_resized = cv2.resize(frame, None, fx=scale, fy=scale)
                undistorted_resized = cv2.resize(undistorted, None, fx=scale, fy=scale)
            else:
                frame_resized = frame
                undistorted_resized = undistorted
            
            comparison = np.hstack([frame_resized, undistorted_resized])
            
            # 显示FPS
            cv2.putText(comparison, f'Frame: {frame_count}', (10, comparison.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('Camera Undistortion - Original vs Corrected', comparison)
        else:
            # 只显示矫正后的完整图像
            display_frame = undistorted.copy()
            cv2.putText(display_frame, f'Undistorted - Frame: {frame_count}', (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow('Undistorted View (Full Frame)', display_frame)
        
        # 按键处理
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("退出程序")
            break
        elif key == ord('s'):
            # 保存矫正后的图像
            filename = f'undistorted_frame_{frame_count}.jpg'
            cv2.imwrite(filename, undistorted)
            filename_orig = f'original_frame_{frame_count}.jpg'
            cv2.imwrite(filename_orig, frame)
            print(f"已保存图像: {filename_orig}, {filename}")
        elif key == ord('c'):
            # 切换显示模式
            show_comparison = not show_comparison
            cv2.destroyAllWindows()
            print(f"切换显示模式: {'对比' if show_comparison else '仅矫正'}")
        elif key == ord('o'):
            # 显示原始图像
            cv2.imshow('Original (No Correction)', frame)
            print("显示原始图像窗口")
        elif key == ord('d'):
            # 切换调试信息
            show_debug = not show_debug
            print(f"调试信息: {'开' if show_debug else '关'}")
            if show_debug:
                print(f"原始图像范围: [{frame.min()}, {frame.max()}]")
                print(f"矫正后图像范围: [{undistorted.min()}, {undistorted.max()}]")
                print(f"非零像素: 原始={np.count_nonzero(frame)}, 矫正后={np.count_nonzero(undistorted)}")
    
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()
    print("程序已结束")


if __name__ == '__main__':
    main()
