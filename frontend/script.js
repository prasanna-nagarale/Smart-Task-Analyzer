// frontend/script.js
const taskList = [];
const taskListEl = document.getElementById("task-list");
const messagesEl = document.getElementById("messages");
const resultsEl = document.getElementById("results");

function showMessage(msg, isError=false){
  messagesEl.textContent = msg;
  messagesEl.style.color = isError ? "#ffb3b3" : "#bfffc4";
  setTimeout(()=> { messagesEl.textContent = ""; }, 6000);
}

function renderLocalList(){
  taskListEl.innerHTML = "";
  taskList.forEach((t, idx) => {
    const li = document.createElement("li");
    li.className = "task-item";
    li.innerHTML = `<div><strong>${t.title}</strong><br><small>${t.due_date || "no due"} • ${t.estimated_hours}h • imp ${t.importance}</small></div>
      <div><button data-idx="${idx}" class="remove-btn">Remove</button></div>`;
    taskListEl.appendChild(li);
  });
  document.querySelectorAll(".remove-btn").forEach(b=>{
    b.onclick = e=>{
      const idx = parseInt(e.target.dataset.idx);
      taskList.splice(idx,1);
      renderLocalList();
    }
  });
}

document.getElementById("add-task").onclick = ()=>{
  const title = document.getElementById("title").value.trim();
  if(!title){ showMessage("Title required", true); return; }
  const due_date = document.getElementById("due_date").value || null;
  const estimated_hours = parseFloat(document.getElementById("estimated_hours").value || 1);
  const importance = parseInt(document.getElementById("importance").value || 5);
  const deps_raw = document.getElementById("dependencies").value.trim();
  const dependencies = deps_raw ? deps_raw.split(",").map(s=>s.trim()).filter(Boolean) : [];
  const id = `t${Date.now()}_${Math.floor(Math.random()*999)}`;
  taskList.push({id, title, due_date, estimated_hours, importance, dependencies});
  renderLocalList();
  document.getElementById("task-form").reset();
}

document.getElementById("clear-list").onclick = ()=>{
  taskList.length = 0;
  renderLocalList();
}

async function postAnalyze(payload, endpoint="/api/tasks/analyze/"){
  resultsEl.innerHTML = "<p>Loading...</p>";
  try{
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    if(!res.ok){
      const txt = await res.text();
      showMessage("Server error: " + txt, true);
      resultsEl.innerHTML = "";
      return null;
    }
    const data = await res.json();
    return data;
  } catch(e){
    showMessage("Network error", true);
    resultsEl.innerHTML = "";
    return null;
  }
}

function renderResults(tasks){
  if(!tasks.length){ resultsEl.innerHTML = "<p>No tasks returned.</p>"; return; }
  resultsEl.innerHTML = "";
  tasks.forEach(t=>{
    const div = document.createElement("div");
    div.className = "result-card";
    const badgeClass = t.priority === "High" ? "badge high" : t.priority === "Medium" ? "badge medium" : "badge low";
    div.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center">
      <div><strong>${t.title}</strong><br><small>${t.due_date || "No due date"} • ${t.estimated_hours}h • imp ${t.importance}</small></div>
      <div style="text-align:right"><span class="${badgeClass}">${t.priority}</span><div style="font-weight:700">${Math.round(t.score*100)}</div></div>
    </div>
    <p style="margin:8px 0"><small>${t.explanation}</small></p>
    <p style="margin:0"><small>Components: U:${t.components.urgency} I:${t.components.importance} E:${t.components.effort} D:${t.components.dependency}</small></p>`;
    resultsEl.appendChild(div);
  });
}

document.getElementById("analyze").onclick = async ()=>{
  let payload = null;
  const bulk = document.getElementById("bulk-json").value.trim();
  if(bulk){
    try{
      const parsed = JSON.parse(bulk);
      if(Array.isArray(parsed)){
        payload = {strategy: document.getElementById("strategy").value, tasks: parsed};
      } else if (parsed && parsed.tasks){
        payload = parsed;
      } else {
        showMessage("Bulk JSON must be an array of tasks or {tasks: [...]}", true);
        return;
      }
    } catch(e){
      showMessage("Invalid JSON in bulk area", true);
      return;
    }
  } else {
    if(taskList.length===0){ showMessage("Add tasks or paste JSON", true); return; }
    payload = {strategy: document.getElementById("strategy").value, tasks: taskList};
  }
  const data = await postAnalyze(payload, "/api/tasks/analyze/");
  if(!data) return;
  if(data.validation_warnings && data.validation_warnings.length){
    showMessage("Validation warnings: " + data.validation_warnings.join("; "), true);
  }
  if(data.warnings && data.warnings.length){
    showMessage("Warnings: " + data.warnings.join("; "), true);
  }
  renderResults(data.tasks);
}

document.getElementById("suggest").onclick = async ()=>{
  let tasksArr = null;
  const bulk = document.getElementById("bulk-json").value.trim();
  if(bulk){
    try{ tasksArr = JSON.parse(bulk); } catch(e){ showMessage("Invalid bulk JSON", true); return; }
  } else {
    if(taskList.length===0){ showMessage("Add tasks or paste JSON", true); return; }
    tasksArr = taskList;
  }
  // POST to suggest endpoint (server also supports GET with urlencoded param)
  const payload = {strategy: document.getElementById("strategy").value, tasks: tasksArr};
  const data = await postAnalyze(payload, "/api/tasks/suggest/");
  if(!data) return;
  if(data.validation_warnings && data.validation_warnings.length){
    showMessage("Validation warnings: " + data.validation_warnings.join("; "), true);
  }
  if(data.warnings && data.warnings.length){
    showMessage("Warnings: " + data.warnings.join("; "), true);
  }
  renderResults(data.suggestions || []);
}
