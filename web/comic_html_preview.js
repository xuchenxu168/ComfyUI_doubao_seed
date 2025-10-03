import { app } from "../../scripts/app.js";

const NODE_NAME = 'ComicHTMLPreviewNode'

app.registerExtension({
    name: "ComicHTMLPreview",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== NODE_NAME) {
            return
        }

        nodeType.prototype.addOrUpdateIframe = function ({
            html,
            width,
            height,
            scale,
            isPortrait
        }) {
            const normalizeWidth = (isPortrait ? width : height) * scale;
            const normalizeHeight = (isPortrait ? height : width) * scale;
            const widthPx = `${normalizeWidth}px`
            const heightPx = `${normalizeHeight}px`


            const node = this;
            function resize() {
                requestAnimationFrame(() => {
                    const sz = node.computeSize();
                    if (sz[1] < node.size[1]) {
                        node.size[1] = normalizeHeight + 20 + sz[1]
                    }
                    node.size[0] = normalizeWidth + 20

                    node.onResize?.(normalizeWidth, normalizeHeight);
                    app.graph.setDirtyCanvas(true, false);
                });
            }
            function refreshIframeSize(iframeEl) {
                iframeEl.style.minWidth = widthPx
                iframeEl.style.minHeight = heightPx
                iframeEl.style.maxWidth = widthPx
                iframeEl.style.maxHeight = heightPx
            }

            if (!this.iframeWidget) {
                const refreshEl = document.createElement("button");
                refreshEl.innerHTML = "refresh"
                refreshEl.style = `
                    height: 24px;
                    max-height: 24px;
                    border: #5a5a5a solid 2px;
                    background: #222222;
                    font-size: 12px;
                    color: #dddddd;
                `
                refreshEl.addEventListener('click', () => {
                    console.log('refresh')
                    iframeEl.srcdoc = ''
                    requestAnimationFrame(() => {
                        iframeEl.srcdoc = html
                    })
                })

                const iframeEl = document.createElement("iframe");
                iframeEl.style.border = 'none'


                const refreshWidget = this.addDOMWidget("Refresh", "div", refreshEl, {
                    minNodeSize: {
                        width: 100,
                        height: 32,
                    },
                    getMinHeight: () => 32,
                    getMaxHeight: () => 32,
                    getHeight: () => 32
                });

                const widget = this.addDOMWidget("html", "customtext", iframeEl, {
                    getValue() {
                        return iframeEl.value;
                    },
                    setValue(v) {
                        iframeEl.srcdoc = v;
                    },
                    getMinHeight: () => 32,
                    getMaxHeight: () => 32,
                    getHeight: () => 32
                });
                widget.iframeEl = iframeEl;
                widget.refreshEl = refreshEl;


                this.iframeWidget = widget;
                refreshIframeSize(iframeEl);
                resize();
            }
            this.iframeWidget.iframeEl.onload = () => {
            }
            refreshIframeSize(this.iframeWidget.iframeEl);
            resize();
            this.iframeWidget.iframeEl.srcdoc = html;
        }



        const sanitizeMessageAttr = (msg, fallback) => Array.isArray(msg) && msg?.length ? msg[0] : fallback
        const sanitizeMessage = message => {
            const html = sanitizeMessageAttr(message?.html, '')
            const width = sanitizeMessageAttr(message?.width, 0)
            const height = sanitizeMessageAttr(message?.height, 0)
            const scale = sanitizeMessageAttr(message?.scale, 1)
            const isPortrait = sanitizeMessageAttr(message?.is_portrait, true)

            return {
                html,
                width,
                height,
                scale,
                isPortrait
            }
        }

        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            onExecuted?.apply(this, arguments);

            this.addOrUpdateIframe(sanitizeMessage(message));
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            onConfigure?.apply(this, arguments);
            if (!this.widgets_values) {
                return;
            }
            const [width, height, scale, isPortrait, html] = this.widgets_values
            if (!html) {
                return;
            }

            this.addOrUpdateIframe(sanitizeMessage({ width, height, scale, isPortrait, html }));
        };
    }
});
