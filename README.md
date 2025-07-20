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
    > 需要校验本地环境是否支持GPU推理 否则使用 CPU

3.  **安装 [duguang-ocr-onnx-v2](models/duguang-ocr-onnx-v2)**

    本项目使用 `duguang-ocr-onnx-v2` 模型进行文字识别，它依赖于 duguang 的 duguang-ocr-onnx-v2 模型。请根据你的操作系统下载并安装它。

    需要下载下面表格中一对文字识别(`rec`)和检测(`det`)模型。
    
    | 模型           | 模型大小      | 模型原始仓库                                                 | 百度网盘下载                                                 | modelscope下载（高速）                                       | 个人评价 |
    | -------------- | ------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | -------- |
    | base_seglink++ | 73.2MB+78MB   | rec[地址](https://modelscope.cn/models/iic/cv_convnextTiny_ocr-recognition-general_damo/summary)，det [地址](https://modelscope.cn/models/iic/cv_resnet18_ocr-detection-line-level_damo/summary) | [地址](https://pan.baidu.com/s/1Vch_5kcL_FqQet5G9pfEJQ?pwd=tjp9) | [v2地址](https://modelscope.cn/models/mscoder/duguang-ocr-onnx-v2) | 9分      |
    | large          | 73.2MB+46.4MB | rec[地址](https://modelscope.cn/models/iic/cv_convnextTiny_ocr-recognition-general_damo/summary)，det [地址](https://www.modelscope.cn/models/iic/cv_resnet18_ocr-detection-db-line-level_damo/summary) | [地址](https://pan.baidu.com/s/1Vch_5kcL_FqQet5G9pfEJQ?pwd=tjp9) | [v2地址](https://modelscope.cn/models/mscoder/duguang-ocr-onnx-v2) | 8分      |
    | small          | 7.4MB+5.2MB   | rec[地址](https://modelscope.cn/models/iic/cv_LightweightEdge_ocr-recognitoin-general_damo/summary)，det [地址](https://www.modelscope.cn/models/iic/cv_proxylessnas_ocr-detection-db-line-level_damo/summary) | [地址](https://pan.baidu.com/s/1Vch_5kcL_FqQet5G9pfEJQ?pwd=tjp9) | [v2地址](https://modelscope.cn/models/mscoder/duguang-ocr-onnx-v2) | 5分      |
    
    >  不同的rec和det可以自由组合使用
4.  **运行项目**

    确保你**处于已激活的虚拟环境**中，然后运行主程序：

    ```bash
    python process_main.py
    ```

## 注意事项

*   请将需要识别的图片素材放置在 `images` 文件夹下（如果需要）。
*   在首次运行时，可能需要根据 duguang-ocr-onnx-v2 模型 的实际路径修改 `main.py` 文件中的配置。 