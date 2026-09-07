import re

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'r') as f:
    content = f.read()

old_func_pattern = r"      function renderDependencyTree\(mod\)\s*\{.*?fileTreePane\.innerHTML\s*=\s*html;\s*\}"
old_func = re.search(old_func_pattern, content, re.DOTALL)
if not old_func:
    print("Could not find function!")
else:
    new_func = """      function renderASTNode(node, depth = 0) {
        if (!node) return '';
        
        let name = node.name || 'Node';
        if (!node.name && node.variable) {
          name = node.variable.display || node.variable.name || 'Node';
        }
        
        let depsStr = '';
        if (node.dependencies && node.dependencies.length > 0) {
          const depNames = node.dependencies.map(d => d.name || 'Unknown').join(', ');
          depsStr = `<span style="color: var(--accent-blue); font-size: 10px; margin-left: 8px;">[uses: ${depNames}]</span>`;
        }

        let html = '';
        if (node.children && node.children.length > 0) {
          html += `
            <details style="margin-top: 4px;" ${depth < 2 ? 'open' : ''}>
              <summary style="cursor: pointer; font-family: 'Fira Code', monospace; font-size: 12px; color: var(--text-secondary); outline: none; user-select: none;">
                <span style="color: #fff;">${name}</span>${depsStr}
              </summary>
              <div style="border-left: 1px solid var(--border); margin-left: 6px; padding-left: 12px;">
                ${node.children.map(c => renderASTNode(c, depth + 1)).join('')}
              </div>
            </details>
          `;
        } else {
          html += `
            <div style="margin-top: 4px; padding-left: 14px; font-family: 'Fira Code', monospace; font-size: 12px; color: var(--text-muted);">
              <span style="color: #cbd5e1;">${name}</span>${depsStr}
            </div>
          `;
        }
        return html;
      }

      function renderDependencyTree(mod) {
        if (!mod) return;
        
        let html = `<div style="font-size: 13px; font-weight: 700; color: #fff; padding: 8px; margin-bottom: 12px; border-bottom: 1px solid var(--border); word-break: break-all;">🌳 Intra-file AST Tree<br><span style="font-size: 11px; color: var(--text-muted); font-family: 'Fira Code', monospace; font-weight: normal;">${mod.id}</span></div>`;
        
        html += `<div style="padding: 0 8px;">`;
        if (mod.code_flow) {
            html += renderASTNode(mod.code_flow);
        } else {
            html += `<div style="color: var(--text-muted); font-size: 12px;">No AST data available.</div>`;
        }
        html += `</div>`;
        
        fileTreePane.innerHTML = html;
      }"""
    content = content.replace(old_func.group(0), new_func)
    with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
        f.write(content)
    print("Replaced!")
