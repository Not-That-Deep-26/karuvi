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
        
        let uuid = '';
        if (node.variable && node.variable.uuid) {
           uuid = node.variable.uuid;
        } else if (nameRaw.includes('id=')) {
           const match = nameRaw.match(/id=([a-f0-9\\-]+)/);
           if (match) uuid = match[1];
        }

        let displayName = (node.variable && node.variable.name) ? node.variable.name : nameRaw;

        let badgeBg = 'rgba(148, 163, 184, 0.1)';
        let badgeColor = '#cbd5e1';
        let badgeBorder = 'rgba(148, 163, 184, 0.3)';
        let badgeText = 'BLOCK';
        
        if (nameRaw.startsWith('def ')) {
            badgeBg = 'rgba(30, 58, 138, 0.3)';
            badgeColor = '#93c5fd';
            badgeBorder = '#1d4ed8';
            badgeText = 'FUNCTION';
            if (displayName === nameRaw) {
               displayName = displayName.replace('def ', '') + '()';
            } else {
               displayName += '()';
            }
        } else if (nameRaw.startsWith('class ')) {
            badgeBg = 'rgba(88, 28, 135, 0.3)';
            badgeColor = '#d8b4fe';
            badgeBorder = '#7e22ce';
            badgeText = 'CLASS';
            if (displayName === nameRaw) displayName = displayName.replace('class ', '');
        } else if (nameRaw.includes('(new assignment')) {
            badgeBg = 'rgba(6, 78, 59, 0.3)';
            badgeColor = '#6ee7b7';
            badgeBorder = '#047857';
            badgeText = 'VAR';
            if (displayName === nameRaw) displayName = displayName.split(' (new assignment')[0];
        } else if (nameRaw.includes('(call)')) {
            badgeBg = 'rgba(120, 53, 15, 0.3)';
            badgeColor = '#fcd34d';
            badgeBorder = '#b45309';
            badgeText = 'CALL';
            if (displayName === nameRaw) displayName = displayName.split(' (call)')[0];
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
              let dName = (d.variable && d.variable.name) ? d.variable.name : (d.name || 'Unknown');
              if (dName.includes(' (new assignment')) dName = dName.split(' (new assignment')[0];
              if (dName.includes(' (call)')) dName = dName.split(' (call)')[0];
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
      }"""
    content = content.replace(old_func.group(0), new_func)
    with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
        f.write(content)
    print("Replaced!")
