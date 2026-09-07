import re

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'r') as f:
    content = f.read()

# 1. Add Monaco Loader to <head>
head_replacement = """  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js"></script>"""
content = re.sub(r'  <link href="https://fonts.googleapis.com.*?  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>', head_replacement, content, flags=re.DOTALL)


# 2. Add Monaco initialization variables and config at the start of the <script> logic
script_init_pattern = r'    <script>\s*// Global state'
script_init_replacement = """    <script>
      // Monaco Editor initialization
      let monacoEditor = null;
      let isMonacoReady = false;
      if (window.require) {
          require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }});
          require(['vs/editor/editor.main'], function() {
              isMonacoReady = true;
          });
      }

      // Global state"""
content = re.sub(script_init_pattern, script_init_replacement, content)


# 3. Remove `highlightPythonSyntax` function entirely
content = re.sub(r'      function highlightPythonSyntax\(rawText\).*?      \}\n', '', content, flags=re.DOTALL)


# 4. Update `window.selectModule`
select_module_pattern = r'        const codeContentEl = document\.getElementById\(\'code-viewer-content\'\);\s*if \(mod\.source_code\) \{.*?          `;\s*\}\s*\}'
select_module_replacement = """        const codeContentEl = document.getElementById('code-viewer-content');
        if (mod.source_code) {
          if (isMonacoReady) {
            if (!monacoEditor) {
                codeContentEl.innerHTML = '';
                monacoEditor = monaco.editor.create(codeContentEl, {
                    value: mod.source_code,
                    language: 'python',
                    theme: 'vs-dark',
                    readOnly: true,
                    automaticLayout: true,
                    minimap: { enabled: false },
                    fontSize: 13,
                    fontFamily: "'Fira Code', monospace",
                    scrollBeyondLastLine: false,
                    padding: { top: 16, bottom: 16 }
                });
            } else {
                monacoEditor.setValue(mod.source_code);
                monacoEditor.setScrollTop(0);
            }
          } else {
            codeContentEl.innerHTML = '<div style="padding: 20px; color: #fff; text-align: center; font-family: monospace;">Loading Monaco Editor...</div>';
            setTimeout(() => window.selectModule(modId), 100);
          }
        } else {
          // Fallback summary if source code not cached
          if (monacoEditor) {
              monacoEditor.dispose();
              monacoEditor = null;
          }
          codeContentEl.innerHTML = `
            <div style="padding: 20px;">
              <h3 style="color: #fff; margin-bottom: 12px;">Module Inspection: ${mod.path}</h3>
              <div class="stat-grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom: 20px;">
                <div class="stat-card"><div class="stat-val">${mod.line_count}</div><div class="stat-lbl">Lines</div></div>
                <div class="stat-card"><div class="stat-val">${mod.function_count}</div><div class="stat-lbl">Functions</div></div>
                <div class="stat-card"><div class="stat-val">${mod.class_count}</div><div class="stat-lbl">Classes</div></div>
              </div>
              <div class="section-title">Functions & Signatures</div>
              <div style="font-family: 'Fira Code', monospace; line-height: 2;">
                ${(mod.functions || []).map(f => `<div>⚡ <span style="color: var(--accent-green);">def</span> <strong>${f.name}</strong>${f.signature || '()'}</div>`).join('') || '<div style="color: var(--text-muted);">None</div>'}
              </div>
            </div>
          `;
        }
      }"""
content = re.sub(select_module_pattern, select_module_replacement, content, flags=re.DOTALL)

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
    f.write(content)
print("Updated visualizer.py with Monaco editor!")
