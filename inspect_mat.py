"""
检查MATLAB .mat文件的结构
"""
from scipy.io import loadmat
import numpy as np

mat_file = r'D:\RM\FSEYE\camera_params_final.mat'

print(f"正在加载: {mat_file}\n")
mat_data = loadmat(mat_file, struct_as_record=False, squeeze_me=True)

print("=" * 60)
print("MAT文件中的所有键:")
print("=" * 60)

for key in mat_data.keys():
    if not key.startswith('__'):
        print(f"\n键名: {key}")
        data = mat_data[key]
        print(f"类型: {type(data)}")
        
        # 如果是结构体，提取字段
        if hasattr(data, '_fieldnames'):
            print(f"字段名: {data._fieldnames}")
            for field in data._fieldnames:
                field_data = getattr(data, field)
                print(f"\n  字段: {field}")
                print(f"  类型: {type(field_data)}")
                if hasattr(field_data, 'shape'):
                    print(f"  形状: {field_data.shape}")
                    print(f"  内容: {field_data}")
                else:
                    print(f"  内容: {field_data}")
