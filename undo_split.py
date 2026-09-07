import re

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'r') as f:
    content = f.read()

# 1. Revert Layout
layout_pattern = r'      <div class="tab-view" id="tab-code">\s*<div class="code-layout" style="display: flex; height: 100%;">\s*<div class="file-tree-pane" id="code-module-tree" style="width: 250px; overflow-y: auto; border-right: 1px solid var\(--border\);"></div>\s*<div class="file-tree-pane" id="code-ast-tree" style="width: 320px; overflow-y: auto; border-right: 1px solid var\(--border\); padding-top: 0;"></div>\s*<div class="code-viewer-pane" id="code-viewer-pane" style="flex: 1; display: flex; flex-direction: column; min-width: 0;">'
layout_replacement = """      <div class="tab-view" id="tab-code">
        <div class="code-layout">
          <div class="file-tree-pane" id="code-file-tree"></div>
          <div class="code-viewer-pane" id="code-viewer-pane">"""
content = re.sub(layout_pattern, layout_replacement, content)

# 2. Revert renderDependencyTree
render_pattern = r'      function renderDependencyTree\(mod\) \{.*?document\.getElementById\(\'code-ast-tree\'\)\.innerHTML = astHtml;\s*\}'

render_replacement = """      function renderDependencyTree(mod) {
        if (!mod) return;
        
        let html = astStyles;
        html += `<div style="font-size: 13px; font-weight: 700; color: #fff; padding: 8px; margin-bottom: 12px; border-bottom: 1px solid var(--border); word-break: break-all;">🌳 Module Explorer<br><span style="font-size: 11px; color: var(--text-muted); font-family: 'Fira Code', monospace; font-weight: normal;">${mod.id}</span></div>`;
        
        // --- Upstream ---
        html += `
          <div style="margin-bottom: 12px; padding: 0 8px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--accent-amber); text-transform: uppercase; padding: 4px 0; cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none';">
              <span style="font-size: 8px;">▼</span> ⬆️ UPSTREAM DEPENDENCIES (${(mod.outgoing_modules || []).length})
            </div>
            <div style="padding-left: 10px;">
        `;
        if (mod.outgoing_modules && mod.outgoing_modules.length > 0) {
            mod.outgoing_modules.forEach(depId => {
              const depMod = (data.modules || []).find(m => m.id === depId);
              const depName = depMod ? depMod.path : depId;
              html += `<div class="file-tree-item" onclick="window.selectModule('${depId}')"><span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📄 ${depName}</span></div>`;
            });
        } else {
            html += `<div style="padding: 4px 0; font-size: 11px; color: var(--text-muted);">None (No imports)</div>`;
        }
        html += `</div></div>`;
        
        // --- Downstream ---
        html += `
          <div style="margin-bottom: 16px; padding: 0 8px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--accent-green); text-transform: uppercase; padding: 4px 0; cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px;" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none';">
              <span style="font-size: 8px;">▼</span> ⬇️ DOWNSTREAM DEPENDENTS (${(mod.incoming_modules || []).length})
            </div>
            <div style="padding-left: 10px;">
        `;
        if (mod.incoming_modules && mod.incoming_modules.length > 0) {
            mod.incoming_modules.forEach(depId => {
              const depMod = (data.modules || []).find(m => m.id === depId);
              const depName = depMod ? depMod.path : depId;
              html += `<div class="file-tree-item" onclick="window.selectModule('${depId}')"><span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📄 ${depName}</span></div>`;
            });
        } else {
            html += `<div style="padding: 4px 0; font-size: 11px; color: var(--text-muted);">None (No dependents)</div>`;
        }
        html += `</div></div>`;
        
        // --- AST Tree ---
        html += `<div style="font-size: 11px; font-weight: 700; color: #fff; padding: 8px; margin-bottom: 4px; border-top: 1px solid var(--border); padding-top: 12px; text-transform: uppercase;">🌳 INTRA-FILE AST TREE</div>`;
        html += `<div style="padding: 0 8px;">`;
        if (mod.code_flow) {
            html += renderASTNode(mod.code_flow);
        } else {
            html += `<div style="color: var(--text-muted); font-size: 12px;">No AST data available.</div>`;
        }
        html += `</div>`;
        
        document.getElementById('code-file-tree').innerHTML = html;
      }"""

content = re.sub(render_pattern, render_replacement, content, flags=re.DOTALL)

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
    f.write(content)
print("Undid visualizer layout split")
