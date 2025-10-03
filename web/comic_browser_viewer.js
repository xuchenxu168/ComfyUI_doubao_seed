// ComicBrowserViewerNode 前端扩展
// 为节点添加"打开浏览器"按钮

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// 注册节点扩展
app.registerExtension({
    name: "ComfyUI.doubao_seed.ComicBrowserViewer",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // 只处理 ComicBrowserViewerNode
        if (nodeData.name !== "ComicBrowserViewerNode") {
            return;
        }
        
        console.log("🌐 注册 ComicBrowserViewerNode 前端扩展");
        
        // 保存原始的 nodeCreated 方法
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        
        // 重写 nodeCreated 方法
        nodeType.prototype.onNodeCreated = function() {
            // 调用原始方法
            const result = onNodeCreated?.apply(this, arguments);
            
            console.log("🌐 ComicBrowserViewerNode 节点已创建");
            
            // 添加"打开浏览器"按钮
            const openBrowserButton = this.addWidget(
                "button",
                "🌐 打开浏览器",
                null,
                () => {
                    // 按钮点击处理
                    this.openInBrowser();
                }
            );
            
            // 设置按钮样式
            openBrowserButton.serialize = false; // 不保存到工作流
            
            // 添加状态显示文本
            const statusWidget = this.addWidget(
                "text",
                "状态",
                "",
                () => {},
                {
                    multiline: true,
                    readonly: true
                }
            );
            statusWidget.serialize = false;
            
            // 保存 widget 引用
            this.openBrowserButton = openBrowserButton;
            this.statusWidget = statusWidget;
            
            // 设置节点颜色
            this.color = "#4A90E2";
            this.bgcolor = "#2C5F8D";
            
            return result;
        };
        
        // 添加打开浏览器的方法
        nodeType.prototype.openInBrowser = async function() {
            console.log("🌐 打开浏览器按钮被点击");
            
            try {
                // 获取 viewer_path 输入
                const viewerPathWidget = this.widgets.find(w => w.name === "viewer_path");
                if (!viewerPathWidget) {
                    this.updateStatus("❌ 错误：找不到 viewer_path 参数");
                    return;
                }
                
                const viewerPath = viewerPathWidget.value;
                if (!viewerPath || viewerPath.trim() === "") {
                    this.updateStatus("❌ 错误：viewer_path 为空\n请先运行工作流生成 HTML 文件");
                    return;
                }
                
                this.updateStatus("🔄 正在打开浏览器...");
                
                // 调用后端 API 打开浏览器
                const response = await api.fetchApi("/doubao_seed/open_browser", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        viewer_path: viewerPath
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.updateStatus(`✅ ${result.message}\n\n文件: ${result.file_path}\nURL: ${result.file_url}`);
                } else {
                    this.updateStatus(`❌ ${result.error}`);
                }
                
            } catch (error) {
                console.error("打开浏览器失败:", error);
                this.updateStatus(`❌ 打开浏览器失败: ${error.message}`);
            }
        };
        
        // 添加更新状态的方法
        nodeType.prototype.updateStatus = function(message) {
            if (this.statusWidget) {
                this.statusWidget.value = message;
                
                // 触发重绘
                if (this.graph && this.graph.setDirtyCanvas) {
                    this.graph.setDirtyCanvas(true, true);
                }
            }
            console.log("📝 状态更新:", message);
        };
        
        // 监听执行完成事件
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(message) {
            const result = onExecuted?.apply(this, arguments);
            
            // 如果有输出，更新状态
            if (message && message.status) {
                this.updateStatus(message.status[0]);
            }
            
            return result;
        };
    }
});

console.log("✅ ComicBrowserViewerNode 前端扩展已加载");

