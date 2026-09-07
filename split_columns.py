import re

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'r') as f:
    content = f.read()

# 1. Update Layout
layout_pattern = r'      <div class="tab-view" id="tab-code">\s*<div class="code-layout">\s*<div class="file-tree-pane" id="code-file-tree"></div>\s*<div class="code-viewer-pane" id="code-viewer-pane">'
layout_replacement = """      <div class="tab-view" id="tab-code">
        <div class="code-layout" style="display: flex; height: 100%;">
          <div class="file-tree-pane" id="code-module-tree" style="width: 250px; overflow-y: auto; border-right: 1px solid var(--border);"></div>
          <div class="file-tree-pane" id="code-ast-tree" style="width: 320px; overflow-y: auto; border-right: 1px solid var(--border); padding-top: 0;"></div>
          <div class="code-viewer-pane" id="code-viewer-pane" style="flex: 1; display: flex; flex-direction: column; min-width: 0;">"""
content = re.sub(layout_pattern, layout_replacement, content)

# 2. Update renderDependencyTree
render_pattern = r'      function renderDependencyTree\(mod\) \{.*?fileTreePane\.innerHTML = html;\s*\}'

render_replacement = """      function renderDependencyTree(mod) {
        if (!mod) return;
        
        // --- COLUMN 1: Module Tree ---
        let modHtml = `<div style="font-size: 13px; font-weight: 700; color: #fff; padding: 8px; margin-bottom: 12px; border-bottom: 1px solid var(--border); word-break: break-all;">🌳 Module Explorer<br><span style="font-size: 11px; color: var(--text-muted); font-family: 'Fira Code', monospace; font-weight: normal;">${mod.id}</span></div>`;
        
        modHtml += `
          <div style="margin-bottom: 12px; padding: 0 8px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--accent-amber); text-transform: uppercase; padding: 4px 0; cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none';">
              <span style="font-size: 8px;">▼</span> ⬆️ UPSTREAM (${(mod.outgoing_modules || []).length})
            </div>
            <div style="padding-left: 10px;">
        `;
        if (mod.outgoing_modules && mod.outgoing_modules.length > 0) {
            mod.outgoing_modules.forEach(depId => {
              const depMod = (data.modules || []).find(m => m.id === depId);
              const depName = depMod ? depMod.path : depId;
              modHtml += `<div class="file-tree-item" onclick="window.selectModule('${depId}')"><span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📄 ${depName}</span></div>`;
            });
        } else {
            modHtml += `<div style="padding: 4px 0; font-size: 11px; color: var(--text-muted);">None</div>`;
        }
        modHtml += `</div></div>`;
        
        modHtml += `
          <div style="margin-bottom: 16px; padding: 0 8px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--accent-green); text-transform: uppercase; padding: 4px 0; cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none';">
              <span style="font-size: 8px;">▼</span> ⬇️ DOWNSTREAM (${(mod.incoming_modules || []).length})
            </div>
            <div style="padding-left: 10px;">
        `;
        if (mod.incoming_modules && mod.incoming_modules.length > 0) {
            mod.incoming_modules.forEach(depId => {
              const depMod = (data.modules || []).find(m => m.id === depId);
              const depName = depMod ? depMod.path : depId;
              modHtml += `<div class="file-tree-item" onclick="window.selectModule('${depId}')"><span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📄 ${depName}</span></div>`;
            });
        } else {
            modHtml += `<div style="padding: 4px 0; font-size: 11px; color: var(--text-muted);">None</div>`;
        }
        modHtml += `</div></div>`;
        
        document.getElementById('code-module-tree').innerHTML = modHtml;

        // --- COLUMN 2: AST Tree ---
        let astHtml = astStyles;
        astHtml += `<div style="font-size: 13px; font-weight: 700; color: #fff; padding: 8px; margin-bottom: 4px; border-bottom: 1px solid var(--border);">AST Symbols</div>`;
        astHtml += `<div style="padding: 8px;">`;
        if (mod.code_flow) {
            astHtml += renderASTNode(mod.code_flow);
        } else {
            astHtml += `<div style="color: var(--text-muted); font-size: 12px;">No AST data available.</div>`;
        }
        astHtml += `</div>`;
        
        document.getElementById('code-ast-tree').innerHTML = astHtml;
      }"""

content = re.sub(render_pattern, render_replacement, content, flags=re.DOTALL)

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
    f.write(content)
print("Updated visualizer layout for columns")
