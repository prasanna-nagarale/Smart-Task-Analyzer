let tasks = [];
let currentResults = [];

const listEl = document.getElementById("task-list");
const msgEl = document.getElementById("messages");
const resEl = document.getElementById("results");
const countEl = document.getElementById("task-count");
const strategySelect = document.getElementById("strategy");
const strategyInfo = document.getElementById("strategy-info");
const matrixViewCheckbox = document.getElementById("matrix-view");

// ==================== STRATEGY DESCRIPTIONS ====================
const STRATEGY_DESCRIPTIONS = {
    smart: "Optimally weighs urgency, importance, effort, and dependencies for well-rounded prioritization.",
    fastest: "Prioritizes low-effort tasks for quick wins and momentum building.",
    high_impact: "Focuses on high-importance tasks regardless of urgency or effort.",
    deadline: "Emphasizes due dates and past-due tasks to meet deadlines."
};

// ==================== HELPERS ====================
function showMsg(msg, isError = false) {
    msgEl.textContent = msg;
    msgEl.className = `message show ${isError ? 'error' : 'success'}`;
    setTimeout(() => {
        msgEl.classList.remove('show');
    }, 5000);
}

function updateTaskCount() {
    countEl.textContent = tasks.length;
}

function renderTasks() {
    listEl.innerHTML = "";
    
    if (tasks.length === 0) {
        listEl.innerHTML = '<li style="text-align: center; color: #a0a8b8; padding: 20px;">No tasks added yet</li>';
        updateTaskCount();
        return;
    }
    
    tasks.forEach((t, i) => {
        const li = document.createElement("li");
        li.className = "task-item";
        li.innerHTML = `
            <span>
                <b>${t.title}</b> • 
                ${t.estimated_hours}h • 
                Importance: ${t.importance}/10
                ${t.due_date ? ` • Due: ${t.due_date}` : ''}
            </span>
            <button onclick="removeTask(${i})">✕</button>
        `;
        listEl.appendChild(li);
    });
    
    updateTaskCount();
}

function removeTask(i) {
    tasks.splice(i, 1);
    renderTasks();
    showMsg("Task removed");
}

// ==================== STRATEGY INFO UPDATE ====================
strategySelect.addEventListener('change', () => {
    const strategy = strategySelect.value;
    strategyInfo.querySelector('p').innerHTML = `<strong>${strategySelect.options[strategySelect.selectedIndex].text.split(' ')[1]}:</strong> ${STRATEGY_DESCRIPTIONS[strategy]}`;
});

// ==================== ADD TASK ====================
document.getElementById("add-task").onclick = () => {
    const title = document.getElementById("title").value.trim();
    
    if (!title) {
        showMsg("❌ Task title is required", true);
        return;
    }

    const dueDate = document.getElementById("due").value || null;
    const hours = parseFloat(document.getElementById("hours").value) || 1;
    const importance = parseInt(document.getElementById("importance").value) || 5;
    const depsInput = document.getElementById("deps").value.trim();
    
    const deps = depsInput ? depsInput.split(",").map(x => x.trim()).filter(Boolean) : [];

    tasks.push({
        id: "task_" + Date.now(),
        title,
        due_date: dueDate,
        estimated_hours: hours,
        importance,
        dependencies: deps
    });

    renderTasks();
    showMsg("✅ Task added successfully!");
    
    // Clear form
    document.getElementById("title").value = "";
    document.getElementById("due").value = "";
    document.getElementById("hours").value = "1";
    document.getElementById("importance").value = "5";
    document.getElementById("deps").value = "";
};

// ==================== CLEAR TASKS ====================
document.getElementById("clear").onclick = () => {
    if (tasks.length === 0) {
        showMsg("⚠️ No tasks to clear", true);
        return;
    }
    
    if (confirm("Are you sure you want to clear all tasks?")) {
        tasks = [];
        renderTasks();
        showMsg("🗑️ All tasks cleared");
    }
};

// ==================== ANALYZE TASKS ====================
document.getElementById("analyze").onclick = async () => {
    const analyzeBtn = document.getElementById("analyze");
    const btnText = analyzeBtn.querySelector(".btn-text");
    const spinner = analyzeBtn.querySelector(".spinner");
    
    let payload = null;
    const json = document.getElementById("json-input").value.trim();

    if (json) {
        try {
            const parsedTasks = JSON.parse(json);
            payload = {
                strategy: strategySelect.value,
                tasks: parsedTasks
            };
        } catch {
            showMsg("❌ Invalid JSON format", true);
            return;
        }
    } else if (tasks.length > 0) {
        payload = {
            strategy: strategySelect.value,
            tasks
        };
    } else {
        showMsg("⚠️ Please add tasks or paste JSON", true);
        return;
    }

    // Loading state
    analyzeBtn.disabled = true;
    btnText.style.display = "none";
    spinner.style.display = "inline-block";

    try {
        const res = await fetch("http://127.0.0.1:8000/api/tasks/analyze/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        
        if (!res.ok) {
            showMsg(`❌ Error: ${data.error || "Failed to analyze tasks"}`, true);
            return;
        }

        currentResults = data.tasks;
        renderResults(currentResults);

        if (data.warnings && data.warnings.length) {
            showMsg(`⚠️ ${data.warnings.join("; ")}`, true);
        } else {
            showMsg("✅ Analysis complete!");
        }

        if (data.validation_warnings && data.validation_warnings.length) {
            console.warn("Validation warnings:", data.validation_warnings);
        }
        
    } catch (error) {
        showMsg("❌ Network error. Is the server running?", true);
        console.error(error);
    } finally {
        // Reset button
        analyzeBtn.disabled = false;
        btnText.style.display = "inline";
        spinner.style.display = "none";
    }
};

// ==================== SUGGEST TOP 3 ====================
document.getElementById("suggest").onclick = async () => {
    const suggestBtn = document.getElementById("suggest");
    const btnText = suggestBtn.querySelector(".btn-text");
    const spinner = suggestBtn.querySelector(".spinner");
    
    if (tasks.length === 0) {
        showMsg("⚠️ Please add tasks first", true);
        return;
    }

    const payload = {
        strategy: strategySelect.value,
        tasks
    };

    // Loading state
    suggestBtn.disabled = true;
    btnText.style.display = "none";
    spinner.style.display = "inline-block";

    try {
        const res = await fetch("http://127.0.0.1:8000/api/tasks/suggest/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        
        if (!res.ok) {
            showMsg(`❌ Error: ${data.error || "Failed to get suggestions"}`, true);
            return;
        }

        currentResults = data.suggestions;
        renderResults(currentResults);

        if (data.warnings && data.warnings.length) {
            showMsg(`⚠️ ${data.warnings.join("; ")}`, true);
        } else {
            showMsg("✨ Top 3 suggestions ready!");
        }
        
    } catch (error) {
        showMsg("❌ Network error. Is the server running?", true);
        console.error(error);
    } finally {
        // Reset button
        suggestBtn.disabled = false;
        btnText.style.display = "inline";
        spinner.style.display = "none";
    }
};

// ==================== RENDER RESULTS ====================
function renderResults(list) {
    if (matrixViewCheckbox.checked) {
        renderMatrixView(list);
        return;
    }
    
    renderListView(list);
}

function renderListView(list) {
    resEl.innerHTML = "";

    if (!list || !list.length) {
        resEl.innerHTML = '<div class="empty-state"><p>👆 Add tasks and click "Analyze" to see prioritized results</p></div>';
        return;
    }

    list.forEach((t, index) => {
        const div = document.createElement("div");
        div.className = `result-card ${t.priority.toLowerCase()}`;

        const rankEmoji = index === 0 ? "🥇" : index === 1 ? "🥈" : index === 2 ? "🥉" : "📌";

        div.innerHTML = `
            <h3>
                ${rankEmoji} ${t.title}
                <span class="badge ${t.priority.toLowerCase()}">${t.priority}</span>
            </h3>
            <p><b>Priority Score:</b> ${(t.score * 100).toFixed(1)}%</p>
            <p><b>Analysis:</b> ${t.explanation}</p>
            ${t.in_cycle ? '<p style="color: #ff6b6b;">⚠️ <b>Warning:</b> Part of circular dependency</p>' : ''}
            <small>
                🎯 Urgency: ${(t.components.urgency * 100).toFixed(0)}% • 
                💎 Importance: ${(t.components.importance * 100).toFixed(0)}% • 
                ⚡ Effort: ${(t.components.effort * 100).toFixed(0)}% • 
                🔗 Dependency: ${(t.components.dependency * 100).toFixed(0)}%
            </small>
        `;

        resEl.appendChild(div);
    });
}

// ==================== EISENHOWER MATRIX VIEW ====================
function renderMatrixView(list) {
    resEl.innerHTML = "";

    if (!list || !list.length) {
        resEl.innerHTML = '<div class="empty-state"><p>👆 Add tasks and click "Analyze" to see prioritized results</p></div>';
        return;
    }

    // Calculate median importance for splitting
    const importanceValues = list.map(t => t.components.importance).sort((a, b) => a - b);
    const urgencyValues = list.map(t => t.components.urgency).sort((a, b) => a - b);
    
    const importanceMedian = importanceValues[Math.floor(importanceValues.length / 2)] || 0.5;
    const urgencyMedian = urgencyValues[Math.floor(urgencyValues.length / 2)] || 0.5;

    // Categorize tasks
    const quadrants = {
        urgentImportant: [],
        notUrgentImportant: [],
        urgentNotImportant: [],
        notUrgentNotImportant: []
    };

    list.forEach(t => {
        const isUrgent = t.components.urgency >= urgencyMedian;
        const isImportant = t.components.importance >= importanceMedian;

        if (isUrgent && isImportant) {
            quadrants.urgentImportant.push(t);
        } else if (!isUrgent && isImportant) {
            quadrants.notUrgentImportant.push(t);
        } else if (isUrgent && !isImportant) {
            quadrants.urgentNotImportant.push(t);
        } else {
            quadrants.notUrgentNotImportant.push(t);
        }
    });

    const matrixHTML = `
        <div class="matrix-container">
            <div class="matrix-quadrant urgent-important">
                <h3>🔥 Do First (Urgent & Important)</h3>
                ${renderMatrixTasks(quadrants.urgentImportant)}
            </div>
            <div class="matrix-quadrant not-urgent-important">
                <h3>📅 Schedule (Not Urgent & Important)</h3>
                ${renderMatrixTasks(quadrants.notUrgentImportant)}
            </div>
            <div class="matrix-quadrant urgent-not-important">
                <h3>👥 Delegate (Urgent & Not Important)</h3>
                ${renderMatrixTasks(quadrants.urgentNotImportant)}
            </div>
            <div class="matrix-quadrant not-urgent-not-important">
                <h3>🗑️ Eliminate (Not Urgent & Not Important)</h3>
                ${renderMatrixTasks(quadrants.notUrgentNotImportant)}
            </div>
        </div>
    `;

    resEl.innerHTML = matrixHTML;
}

function renderMatrixTasks(tasks) {
    if (!tasks.length) {
        return '<p style="color: #a0a8b8; font-size: 0.85rem; margin-top: 8px;">No tasks in this quadrant</p>';
    }

    return tasks.map(t => `
        <div class="matrix-task">
            <strong>${t.title}</strong>
            <span style="color: #a0a8b8;">Score: ${(t.score * 100).toFixed(0)}%</span>
        </div>
    `).join('');
}

// ==================== MATRIX VIEW TOGGLE ====================
matrixViewCheckbox.addEventListener('change', () => {
    if (currentResults.length > 0) {
        renderResults(currentResults);
    }
});

// ==================== INITIALIZE ====================
renderTasks();
updateTaskCount();