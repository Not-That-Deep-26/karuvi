import re

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'r') as f:
    content = f.read()

broken_code = """      window.jumpToGraphNode = function(modId) {
        switchTab('graph');
        currentLevel = 'modules';
              network.selectNodes([`mod:${modId}`]);
            applyUnrelatedNodeGreying(`mod:${modId}`);
            onCanvasNodeSelected(`mod:${modId}`);
          }
        }, 200);
      };


      });"""

fixed_code = """      window.jumpToGraphNode = function(modId) {
        switchTab('graph');
        currentLevel = 'modules';
        updateNetworkData();
        setTimeout(() => {
          if (network) {
            network.focus(`mod:${modId}`, { scale: 1.2, animation: { duration: 500 } });
            network.selectNodes([`mod:${modId}`]);
            applyUnrelatedNodeGreying(`mod:${modId}`);
          }
        }, 200);
      };"""

content = content.replace(broken_code, fixed_code)

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
    f.write(content)
