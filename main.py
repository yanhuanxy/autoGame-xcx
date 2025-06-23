import time
from core import window
from modules import trial, boss, experience, spacetime, daily

# --- 配置 ---
TARGET_APP_NAME = "聊斋搜神记"

# --- 初始化 ---
def initialize():
    """
    初始化 Tesseract 和查找目标窗口
    """
    print("正在初始化...")

    # 查找目标窗口
    hwnd = window.find_target_window(TARGET_APP_NAME)
    if not hwnd:
        print(f"错误：未找到名为 '{TARGET_APP_NAME}' 的应用程序。")
        return None

    print(f"成功找到窗口，句柄: {hwnd}")
    window.activate_window(hwnd)
    time.sleep(1) # 等待窗口激活
    return hwnd

# --- 主程序 ---
def main():
    """
    主函数，编排整个自动化流程
    """
    hwnd = initialize()
    if not hwnd:
        return

    # --- 任务调度 ---
    # 按顺序执行各个模块
    # 未来可以改为根据配置文件或用户输入来决定执行哪些任务

    tasks = [
        trial.run,
        boss.run,
        experience.run,
        spacetime.run,
        daily.run # daily是待实现的模块
    ]

    for task in tasks:
        try:
            task(hwnd)
        except Exception as e:
            print(f"执行任务 {task.__module__} 时发生错误: {e}")
        time.sleep(2) # 每个大模块操作后给予一定延时

    print("\n所有任务执行完毕。")

if __name__ == "__main__":
    main()