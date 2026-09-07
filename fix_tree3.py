import re

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'r') as f:
    content = f.read()

old_func_pattern = r"      const astStyles = `.*?fileTreePane\.innerHTML = html;\s*\}"
old_func = re.search(old_func_pattern, content, re.DOTALL)
if not old_func:
    print("Could not find function!")
else:
    new_func = """      const astStyles = `
        <style>
          .ast-node {
            font-family: 'Fira Code', monospace;
            font-size: 12px;
            position: relative;
          }
          .ast-summary {
            cursor: pointer;
            outline: none;
            user-select: none;
            display: inline-flex;
            align-items: center;
            padding: 2px 4px;
            border-radius: 4px;
            transition: background 0.2s;
          }
          .ast-summary:hover {
            background: rgba(255,255,255,0.05);
          }
          .ast-children {
            margin-left: 8px;
            padding-left: 12px;
            border-left: 1px solid rgba(255,255,255,0.15);
          }
          .ast-item-wrapper {
            position: relative;
          }
          .ast-item-wrapper::before {
            content: '';
            position: absolute;
            top: 10px;
            left: -12px;
            width: 12px;
            height: 1px;
            border-top: 1px solid rgba(255,255,255,0.15);
            z-index: 1;
          }
          .ast-badge {
            font-size: 9px;
            padding: 1px 4px;
            border-radius: 4px;
            margin-right: 6px;
            font-weight: 700;
            letter-spacing: 0.2px;
            display: inline-block;
          }
          .ast-symbol {
            color: #f8fafc;
            font-weight: 400;
            letter-spacing: 0.2px;
            z-index: 2;
            position: relative;
          }
          .ast-uuid {
            font-size: 9px;
            color: rgba(255,255,255,0.2);
            margin-bottom: 2px;
            font-family: monospace;
          }
        </style>
      `;

      function renderASTNode(node, depth = 0) {
        if (!node) return '';
        
        let nameRaw = node.name || 'Node';
        if (!node.name && node.variable) {
          nameRaw = node.variable.display || node.variable.name || 'Node';
        }
        
        let uuid = '';
        if (nameRaw.includes('id=')) {
           const match = nameRaw.match(/id=([a-f0-9\\-]+)/);
           if (match) uuid = match[1];
        } else if (node.variable && node.variable.uuid) {
           uuid = node.variable.uuid;
        }

        let badgeBg = 'rgba(148, 163, 184, 0.1)';
        let badgeColor = '#cbd5e1';
        let badgeBorder = 'rgba(148, 163, 184, 0.3)';
        let badgeText = 'BLOCK';
        
        let displayName = nameRaw;
        
        if (displayName.startsWith('def ')) {
            badgeBg = 'rgba(30, 58, 138, 0.3)';
            badgeColor = '#93c5fd';
            badgeBorder = '#1d4ed8';
            badgeText = 'FUNCTION';
            displayName = displayName.replace('def ', '') + '()';
        } else if (displayName.startsWith('class ')) {
            badgeBg = 'rgba(88, 28, 135, 0.3)';
            badgeColor = '#d8b4fe';
            badgeBorder = '#7e22ce';
            badgeText = 'CLASS';
            displayName = displayName.replace('class ', '');
        } else if (displayName.includes('(new assignment')) {
            badgeBg = 'rgba(6, 78, 59, 0.3)';
            badgeColor = '#6ee7b7';
            badgeBorder = '#047857';
            badgeText = 'VAR';
            displayName = displayName.split(' (new assignment')[0];
        } else if (displayName.includes('(call)')) {
            badgeBg = 'rgba(120, 53, 15, 0.3)';
            badgeColor = '#fcd34d';
            badgeBorder = '#b45309';
            badgeText = 'CALL';
            displayName = displayName.split(' (call)')[0];
        } else if (displayName === 'Module Start' || displayName === 'Node') {
            if (displayName === 'Node') displayName = 'Block';
        }

        // Flatten blocks
        if (displayName === 'Block' || displayName === 'Module Start') {
            if (node.children && node.children.length > 0) {
                return node.children.map(c => renderASTNode(c, depth)).join('');
            }
            return '';
        }

        let badgeHtml = `<span class="ast-badge" style="background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBorder};">${badgeText}</span>`;

        let depsStr = '';
        if (node.dependencies && node.dependencies.length > 0) {
          const depNames = node.dependencies.map(d => {
              let dName = d.name || 'Unknown';
              return `<span style="color: #94a3b8;">${dName}</span>`;
          }).join(', ');
          depsStr = `<div style="font-size: 10px; color: var(--text-muted); margin-bottom: 4px; display: flex; align-items: center; gap: 4px;">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-blue); opacity: 0.5;"><polyline points="15 10 20 15 15 20"></polyline><path d="M4 4v7a4 4 0 0 0 4 4h12"></path></svg>
            ${depNames}
          </div>`;
        }

        let html = '';
        const lineLoc = (node.variable && node.variable.reference) ? ` <span style="color: var(--text-muted); font-size: 9px; margin-left: 6px; opacity: 0.5; font-weight: normal;">L${node.variable.reference.line}</span>` : '';

        const isRoot = depth === 0;
        const uuidHtml = uuid ? `<div class="ast-uuid">${uuid}</div>` : '';

        if ((node.children && node.children.length > 0) || depsStr || uuid) {
          html += `
            <div class="${isRoot ? '' : 'ast-item-wrapper'}">
              <details class="ast-node" style="margin-top: ${isRoot ? '0' : '2px'};" ${depth < 3 ? 'open' : ''}>
                <summary class="ast-summary">
                  <div style="display: inline-flex; align-items: center; vertical-align: middle;">
                      ${badgeHtml}
                      <span class="ast-symbol">${displayName}</span>
                      ${lineLoc}
                  </div>
                </summary>
                <div class="ast-children">
                  ${uuidHtml}
                  ${depsStr}
                  ${(node.children || []).map(c => renderASTNode(c, depth + 1)).join('')}
                </div>
              </details>
            </div>
          `;
        } else {
          html += `
            <div class="${isRoot ? '' : 'ast-item-wrapper'}">
              <div class="ast-node" style="margin-top: ${isRoot ? '0' : '2px'}; padding: 2px 4px;">
                <div style="display: flex; align-items: center; width: 100%;">
                  ${badgeHtml}
                  <span class="ast-symbol">${displayName}</span>
                  ${lineLoc}
                </div>
              </div>
            </div>
          `;
        }
        return html;
      }

      function renderDependencyTree(mod) {
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
        
        fileTreePane.innerHTML = html;
      }"""
    content = content.replace(old_func.group(0), new_func)
    with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
        f.write(content)
    print("Replaced!")
