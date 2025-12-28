// Main JS for Job App Assistant

document.addEventListener('DOMContentLoaded', () => {
    // File upload handler
    const fileInput = document.getElementById('cvFile');
    const fileNameDisplay = document.getElementById('fileName');

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                fileNameDisplay.textContent = e.target.files[0].name;
                const formData = new FormData();
                formData.append('file', e.target.files[0]);

                fetch('/api/step3/upload', {
                    method: 'POST',
                    body: formData
                })
                    .then(r => r.json())
                    .then(data => {
                        appendLog('Fichier chargé : ' + data.filename);
                    })
                    .catch(err => appendLog('Erreur upload: ' + err));
            }
        });
    }

    // Validated poller
    // Validated poller
    setInterval(pollLogs, 1000);
});

// Tab Switching Logic
let currentTab = 'keyword';

function switchTab(tab) {
    currentTab = tab;

    // UI Update
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => {
        c.style.display = 'none';
        c.classList.remove('active');
    });

    // Button active
    // We assume buttons have correct onclick: switchTab('keyword'), switchTab('url'), switchTab('raw_text')
    const buttons = document.getElementsByClassName('tab-btn');
    if (tab === 'keyword') {
        buttons[0].classList.add('active');
    } else if (tab === 'url') {
        buttons[1].classList.add('active');
    } else {
        buttons[2].classList.add('active');
    }

    // Content active
    const content = document.getElementById('tab-' + tab);
    if (content) {
        content.style.display = 'block';
        content.classList.add('active');
    }
}

async function runStep1() {
    let mode = 'scrape';
    let keyword = '';
    let text = '';

    if (currentTab === 'keyword') {
        keyword = document.getElementById('keyword_input').value;
        mode = 'scrape';
    } else if (currentTab === 'url') {
        keyword = document.getElementById('url_input').value;
        mode = 'scrape';
    } else {
        text = document.getElementById('raw_text_input').value;
        mode = 'text';
    }

    const num = document.getElementById('num_jobs').value;

    resetStatus('status1');
    try {
        await fetch('/api/step1', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode: mode,
                keyword: keyword,
                num_jobs: num,
                text: text
            })
        });
    } catch (e) { console.error(e); }
}

async function runStep2() {
    resetStatus('status2');
    await fetch('/api/step2', { method: 'POST' });
}

async function runStep3() {
    const fileName = document.getElementById('fileName').textContent;
    if (fileName === "Aucun fichier") {
        alert("Veuillez sélectionner un fichier PDF d'abord.");
        return;
    }
    resetStatus('status3');
    await fetch('/api/step3', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: fileName })
    });
}

async function runStep4() {
    resetStatus('status4');
    await fetch('/api/step4', { method: 'POST' });
}

async function runStep5() {
    resetStatus('status5');
    await fetch('/api/step5', { method: 'POST' });
}

async function runStep6() {
    resetStatus('status6');
    await fetch('/api/step6', { method: 'POST' });
}

function resetStatus(id) {
    document.getElementById(id).textContent = "En cours...";
    document.getElementById(id).className = "status-indicator status-running";
    // Clear preview
    const stepNum = id.replace('status', '');
    const preview = document.getElementById('preview' + stepNum);
    if (preview) preview.innerHTML = '';
}

function markCompleted(taskName) {
    // taskName is 'step1', 'step2'...
    const num = taskName.replace('step', '');
    const statusEl = document.getElementById('status' + num);
    if (statusEl) {
        statusEl.textContent = "Terminé";
        statusEl.className = "status-indicator status-completed";
    }
    fetchPreview(taskName);
}

function markError(taskName, msg) {
    const num = taskName.replace('step', '');
    const statusEl = document.getElementById('status' + num);
    if (statusEl) {
        statusEl.textContent = "Erreur";
        statusEl.className = "status-indicator status-error";
    }
}

async function fetchPreview(taskName) {
    const num = taskName.replace('step', '');
    const previewEl = document.getElementById('preview' + num);

    if (!previewEl) return;

    try {
        const res = await fetch('/api/preview/' + taskName);
        const data = await res.json();

        if (data.error) {
            previewEl.textContent = "Erreur preview: " + data.error;
            return;
        }

        let html = '';

        if (taskName === 'step5' || taskName === 'step6') {
            // Special detailed view for Matching
            html = '<div class="match-results">';
            data.forEach(row => {
                const score = parseFloat(row.match_score).toFixed(1);
                let scoreClass = 'score-low';
                if (score > 70) scoreClass = 'score-high';
                else if (score > 50) scoreClass = 'score-mid';

                html += `
               <div class="match-card">
                   <div class="match-header">
                       <div class="match-info">
                           <strong>${row.Poste}</strong>
                           <span class="company">${row.Entreprise}</span>
                       </div>
                       <div class="match-score ${scoreClass}">${score}%</div>
                   </div>
                   <div class="match-details">
                       <p><strong>IA Résumé:</strong> ${row.Resume_IA || 'N/A'}</p>
                       <a href="${row.Lien}" target="_blank" class="match-link">Voir l'offre →</a>
                   </div>
               </div>`;
            });
            html += '</div>';
        } else if (Array.isArray(data)) {
            // Standard table for Step 1 & 2
            html = '<div class="preview-table">';
            data.forEach(row => {
                html += '<div class="preview-row">';
                Object.keys(row).forEach(k => {
                    if (k === 'Resume_IA') {
                        html += `<div style="margin-top:5px; padding:5px; background: #2a2a40; border-radius:4px;">
                                    <strong>Résumé IA:</strong> <span style="font-size:0.9em; color:#ddd;">${row[k]}</span>
                                 </div>`;
                    } else {
                        html += `<div><strong>${k}:</strong> ${row[k]}</div>`;
                    }
                });
                html += '</div>';
            });
            html += '</div>';
        } else if (data.content) {
            // Text preview (Steps 3 & 4)
            html = `<pre style="white-space: pre-wrap; font-size: 0.75rem;">${data.content}</pre>`;
        }

        previewEl.innerHTML = html;
        previewEl.style.display = 'block';

    } catch (e) {
        console.error(e);
    }
}

// Logic to track state changes
let currentKnownState = "IDLE";
let currentActiveTask = null;

async function pollLogs() {
    try {
        const res = await fetch('/api/logs?t=' + Date.now());
        const data = await res.json();

        // Logs
        const logsWindow = document.getElementById('logsWindow');
        const newLogs = data.logs;
        // Simple log appending (clearing if reset)
        logsWindow.innerHTML = '';
        newLogs.forEach(msg => {
            const div = document.createElement('div');
            div.className = 'log-line';
            div.textContent = `> ${msg}`;
            logsWindow.appendChild(div);
        });
        logsWindow.scrollTop = logsWindow.scrollHeight;

        // State Machine
        const serverState = data.task_state; // IDLE, RUNNING, COMPLETED, ERROR
        const serverTask = data.active_task;

        console.log(`State: ${serverState}, Task: ${serverTask}`); // Debug

        // Reconciliation Logic: Ensure UI matches Server State
        if (serverState === "COMPLETED" && serverTask) {
            const num = serverTask.replace('step', '');
            const statusEl = document.getElementById('status' + num);
            // If server is done but UI is not marked done, force update
            if (statusEl && statusEl.textContent !== "Terminé") {
                console.log("State mismatch detected, forcing completion update");
                markCompleted(serverTask);
            }
        } else if (serverState === "ERROR" && serverTask) {
            const num = serverTask.replace('step', '');
            const statusEl = document.getElementById('status' + num);
            if (statusEl && statusEl.textContent !== "Erreur") {
                markError(serverTask, "Erreur détéctée");
            }
        }

        currentKnownState = serverState;
        currentActiveTask = serverTask;

    } catch (e) {
        console.error("Log polling error", e);
    }
}

function appendLog(message) {
    // Deprecated for full refresh in pollLogs to handle clear()
}
