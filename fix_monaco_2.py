import re

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'r') as f:
    content = f.read()

# Replace the start of the IIFE
script_init_pattern = r'    \(function\(\) \{\n      const data = window\.KARUVI_DATA;'
script_init_replacement = """    (function() {
      // Monaco Editor initialization
      let monacoEditor = null;
      let isMonacoReady = false;
      if (window.require) {
          require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }});
          require(['vs/editor/editor.main'], function() {
              isMonacoReady = true;
          });
      }

      const data = window.KARUVI_DATA;"""
content = re.sub(script_init_pattern, script_init_replacement, content)

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
    f.write(content)
print("Injected Monaco initialization!")
