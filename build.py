import PyInstaller.__main__
import platform
import os
import shutil

def clean_build_dirs():
    dirs_to_clean = ['build', 'dist']
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d)

def build():
    print("开始清理旧的构建文件... / Starting to clean old build files...")
    clean_build_dirs()
    
    print("准备打包 Vibe Mouse... / Preparing to build Vibe Mouse...")
    
    system = platform.system()
    
    # 基础 PyInstaller 参数
    # Basic PyInstaller arguments
    args = [
        'core/main.py',
        '--name=VibeMouse',
        '--onefile',           # 打包成单文件 / Package as a single file
        '--noconsole',         # 隐藏控制台窗口 / Hide console window
        '--clean'              # 清理临时文件 / Clean temporary files
    ]
    
    if system == "Windows":
        # Windows 特定设置 / Windows specific settings
        print("检测到 Windows 系统，正在构建 exe... / Windows detected, building exe...")
        # 可以添加 --icon=icon.ico 如果有图标文件的话
        # Can add --icon=icon.ico if you have an icon file
        
    elif system == "Darwin":
        # macOS 特定设置 / macOS specific settings
        print("检测到 macOS 系统，正在构建 app... / macOS detected, building app...")
        args.append('--windowed') # macOS 的 windowed 模式 / windowed mode for macOS
    
    else:
        print(f"在 {system} 系统上进行标准构建... / Standard build on {system}...")
        
    # 执行打包
    # Execute build
    PyInstaller.__main__.run(args)
    
    print("\n打包完成！可执行文件位于 'dist' 目录下。 / Build complete! The executable is located in the 'dist' directory.")

if __name__ == "__main__":
    build()
