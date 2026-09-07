import re

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'r') as f:
    content = f.read()

old_func_pattern = r"      function renderASTNode\(node, depth = 0\) \{.*?return html;\s*\}"
old_func = re.search(old_func_pattern, content, re.DOTALL)
if not old_func:
    print("Could not find function!")
else:
    new_func = """      function renderASTNode(node, depth = 0) {
        if (!node) return '';
        
        let nameRaw = node.name || 'Node';
        if (!node.name && node.variable) {
          nameRaw = node.variable.display || node.variable.name || 'Node';
        }
        
        let icon = '🔹';
        let color = '#e2e8f0'; // default text color
        let tag = '';
        
        // Parse the name for types and clean it up
        let displayName = nameRaw;
        
        if (displayName.startsWith('def ')) {
            icon = '⚡';
            color = '#60a5fa';
            displayName = displayName.replace('def ', '') + '()';
            tag = '<span style="background: rgba(96, 165, 250, 0.1); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.2); padding: 1px 6px; border-radius: 10px; font-size: 9px; margin-left: 6px;">Function</span>';
        } else if (displayName.startsWith('class ')) {
            icon = '📦';
            color = '#c084fc';
            displayName = displayName.replace('class ', '');
            tag = '<span style="background: rgba(192, 132, 252, 0.1); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.2); padding: 1px 6px; border-radius: 10px; font-size: 9px; margin-left: 6px;">Class</span>';
        } else if (displayName.includes('(new assignment')) {
            icon = '📝';
            color = '#34d399';
            displayName = displayName.split(' (new assignment')[0];
            tag = '<span style="background: rgba(52, 211, 153, 0.1); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.2); padding: 1px 6px; border-radius: 10px; font-size: 9px; margin-left: 6px;">Assignment</span>';
        } else if (displayName.includes('(call)')) {
            icon = '📞';
            color = '#fbbf24';
            displayName = displayName.split(' (call)')[0];
            tag = '<span style="background: rgba(251, 191, 36, 0.1); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.2); padding: 1px 6px; border-radius: 10px; font-size: 9px; margin-left: 6px;">Call</span>';
        } else if (displayName === 'Module Start' || displayName === 'Node') {
            icon = '📄';
            color = '#94a3b8';
            if (displayName === 'Node') displayName = 'Block';
        }

        let depsStr = '';
        if (node.dependencies && node.dependencies.length > 0) {
          const depNames = node.dependencies.map(d => {
              let dName = d.name || 'Unknown';
              return `<span style="color: #94a3b8;">${dName}</span>`;
          }).join(', ');
          depsStr = `<div style="font-size: 10px; color: var(--text-muted); margin-top: 4px; margin-left: 20px; display: flex; align-items: center; gap: 4px;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-blue); opacity: 0.7;"><polyline points="15 10 20 15 15 20"></polyline><path d="M4 4v7a4 4 0 0 0 4 4h12"></path></svg>
            ${depNames}
          </div>`;
        }

        let html = '';
        const lineLoc = (node.variable && node.variable.reference) ? ` <span style="color: var(--text-muted); font-size: 10px; margin-left: 6px; opacity: 0.7;">(Line ${node.variable.reference.line})</span>` : '';

        if (node.children && node.children.length > 0) {
          html += `
            <details style="margin-top: 6px; font-family: 'Fira Code', monospace;" ${depth < 3 ? 'open' : ''}>
              <summary style="cursor: pointer; font-size: 12px; outline: none; user-select: none; padding: 4px 6px; border-radius: 4px; transition: background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'">
                <div style="display: inline-flex; align-items: center; vertical-align: middle;">
                    <span style="margin-right: 6px; font-size: 12px;">${icon}</span>
                    <span style="color: ${color}; font-weight: 500; letter-spacing: 0.2px;">${displayName}</span>
                    ${lineLoc}
                    ${tag}
                </div>
              </summary>
              ${depsStr}
              <div style="border-left: 1px dashed rgba(255,255,255,0.15); margin-left: 14px; padding-left: 10px;">
                ${node.children.map(c => renderASTNode(c, depth + 1)).join('')}
              </div>
            </details>
          `;
        } else {
          html += `
            <div style="margin-top: 4px; font-family: 'Fira Code', monospace; font-size: 12px; padding: 4px 6px 4px 18px; border-radius: 4px; transition: background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'">
              <div style="display: flex; align-items: center; width: 100%;">
                <span style="margin-right: 6px; font-size: 12px;">${icon}</span>
                <span style="color: ${color}; font-weight: 500; letter-spacing: 0.2px;">${displayName}</span>
                ${lineLoc}
                ${tag}
              </div>
              ${depsStr}
            </div>
          `;
        }
        return html;
      }"""
    content = content.replace(old_func.group(0), new_func)
    with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
        f.write(content)
    print("Replaced!")
