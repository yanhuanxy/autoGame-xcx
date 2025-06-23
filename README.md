# autoGame-LZ

一个用于自动化操作桌面应用程序的 Python 项目。

## 功能

*   检测并列出当前系统中正在运行的窗口。
*   允许用户选择要进行自动化操作的目标应用程序窗口。
*   在指定的窗口内进行图像识别和文字识别。
*   根据识别结果，模拟鼠标点击操作。

## 安装与使用

1.  **创建并激活虚拟环境**

    本项目推荐在独立的 Python 虚拟环境中运行，以避免依赖冲突。

    ```powershell
    # 进入项目目录
    cd autoGame-LZ

    # 创建虚拟环境 (如果 venv 文件夹不存在)
    python -m venv venv

    # 激活虚拟环境 (在 Windows PowerShell 中)
    .\venv\Scripts\Activate.ps1
    ```
    *如果激活失败，提示"因为在此系统上禁止运行脚本"，请先在 PowerShell 中运行以下命令，然后再重新激活：*
    `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`

    *激活成功后，你会在命令行提示符前看到 `(venv)` 字样。*

2.  **安装依赖**

    在**已激活**的虚拟环境中，运行以下命令安装项目所需的库：

    ```bash
    pip install -r requirements.txt
    ```

3.  **安装 Tesseract-OCR**

    本项目使用 `pytesseract` 库进行文字识别，它依赖于 Google 的 Tesseract-OCR 引擎。请根据你的操作系统下载并安装它。

    *   [Tesseract 安装文档](https://tesseract-ocr.github.io/tessdoc/Installation.html)
    *   在安装过程中，请记住 Tesseract 的安装路径，我们稍后需要在代码中配置它。

4.  **运行项目**

    确保你**处于已激活的虚拟环境**中，然后运行主程序：

    ```bash
    python main.py
    ```

## 注意事项

*   请将需要识别的图片素材放置在 `images` 文件夹下（如果需要）。
*   在首次运行时，可能需要根据 Tesseract 的实际安装路径修改 `main.py` 文件中的配置。 