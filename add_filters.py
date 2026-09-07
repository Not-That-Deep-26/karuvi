import re

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'r') as f:
    content = f.read()

# 1. HTML Insertion
html_old = """              <div style="display: flex; gap: 8px; align-items: center;">
                <input type="text" id="graph-text-filter" placeholder="Filter nodes..." style="background: var(--bg-surface); border: 1px solid var(--border); color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 12px; width: 160px;">
              </div>"""

html_new = """              <div style="display: flex; gap: 8px; align-items: center;">
                <input type="text" id="graph-text-filter" placeholder="Filter nodes..." style="background: var(--bg-surface); border: 1px solid var(--border); color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 12px; width: 160px;">
                <div style="display: flex; gap: 4px; align-items: center; margin-left: 8px;" id="graph-role-filters">
                  <span class="pill-opt active" data-role="ALL">All</span>
                  <span class="pill-opt" data-role="ENTRY_CANDIDATE">Entry</span>
                  <span class="pill-opt" data-role="CYCLE">Cycle</span>
                  <span class="pill-opt" data-role="HUB">Hub</span>
                  <span class="pill-opt" data-role="BRIDGE">Bridge</span>
                  <span class="pill-opt" data-role="LEAF">Leaf</span>
                </div>
              </div>"""

content = content.replace(html_old, html_new)


# 2. JS Initialization & logic
js_old = """      document.getElementById('graph-text-filter').addEventListener('input', applyTextFilter);

      function applyTextFilter() {
        if (!network) return;
        const query = document.getElementById('graph-text-filter').value.trim().toLowerCase();
        const allNodes = network.body.data.nodes.get();
        const updates = allNodes.map(n => {
          if (!query || (n.label && n.label.toLowerCase().includes(query))) {
            return { id: n.id, opacity: 1.0 };
          } else {
            return { id: n.id, opacity: 0.12 };
          }
        });
        network.body.data.nodes.update(updates);
      }"""

js_new = """      let currentRoleFilter = 'ALL';
      const cyclesSet = new Set();
      (data.cycles || []).forEach(cycle => cycle.forEach(m => cyclesSet.add(m)));

      document.querySelectorAll('#graph-role-filters .pill-opt').forEach(pill => {
        pill.addEventListener('click', () => {
          document.querySelectorAll('#graph-role-filters .pill-opt').forEach(p => p.classList.remove('active'));
          pill.classList.add('active');
          currentRoleFilter = pill.dataset.role;
          applyTextFilter();
        });
      });

      document.getElementById('graph-text-filter').addEventListener('input', applyTextFilter);

      function applyTextFilter() {
        if (!network) return;
        const query = document.getElementById('graph-text-filter').value.trim().toLowerCase();
        const allNodes = network.body.data.nodes.get();
        const updates = allNodes.map(n => {
          let matchesQuery = true;
          let matchesRole = true;

          if (query && !(n.label && n.label.toLowerCase().includes(query))) {
            matchesQuery = false;
          }

          if (currentRoleFilter !== 'ALL' && n.id.startsWith('mod:')) {
            const mId = n.id.replace('mod:', '');
            const mod = (data.modules || []).find(m => m.id === mId);
            if (currentRoleFilter === 'CYCLE') {
              if (!cyclesSet.has(mId)) matchesRole = false;
            } else if (mod && mod.role !== currentRoleFilter) {
              matchesRole = false;
            }
          }

          if (matchesQuery && matchesRole) {
            return { id: n.id, opacity: 1.0 };
          } else {
            return { id: n.id, opacity: 0.12 };
          }
        });
        network.body.data.nodes.update(updates);
      }"""

content = content.replace(js_old, js_new)

with open('/home/tarun/c2c-karuvi/karuvi/architecture/visualizer.py', 'w') as f:
    f.write(content)
