from setuptools import setup, find_packages

setup(
    name="autoGame-xcx",
    version="0.1.0",
    packages=find_packages(),  # 自动发现 core, modules 等包
    install_requires=[
        # 这里写你的依赖，比如
        # "pyautogui",
        # "pytesseract",
        # "opencv-python",
    ],
    python_requires=">=3.7",
    include_package_data=True,
    description="自动化游戏助手"
)