@echo off
chcp 65001 >nul
echo ========================================
echo 安装 PDF 导出支持
echo ========================================
echo.

echo 正在安装 reportlab 库...
echo.
echo 方法 1: 单独安装 reportlab
pip install reportlab
echo.

echo 方法 2: 安装所有依赖（推荐）
echo 如果您想安装所有依赖，请运行：
echo pip install -r requirements.txt
echo.

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 现在您可以使用带文字的 PDF 导出功能了。
echo.
echo 使用方法：
echo 1. 在工作流中添加 ComicBatchExporterNode 节点
echo 2. 设置 export_pdf = true
echo 3. 设置 pdf_with_text = true
echo 4. 运行工作流
echo.
echo 详细说明请查看 PDF导出功能说明.md
echo.
echo 注意：reportlab 已添加到 requirements.txt 中
echo 下次安装时可以直接运行: pip install -r requirements.txt
echo.
pause

