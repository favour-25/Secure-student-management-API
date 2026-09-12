// Base URL of the FastAPI backend. Since the backend now serves this
// dashboard itself, the API lives on the same origin the page was
// loaded from - this works unchanged whether running locally or
// deployed to a live URL.
const API_BASE = window.location.origin;

const loginView = document.getElementById("loginView");
const dashboardView = document.getElementById("dashboardView");
const sessionStatus = document.getElementById("sessionStatus");
const tokenPreview = document.getElementById("tokenPreview");
const requestLog = document.getElementById("requestLog");

// ---------------------------------------------------------------------
// Session helpers
// ---------------------------------------------------------------------

function saveToken(token) {
  localStorage.setItem("access_token", token);
}

function getToken() {
  return localStorage.getItem("access_token");
}

function clearToken() {
  localStorage.removeItem("access_token");
}

function logRequest(method, url, headerSent) {
  const line = document.createElement("div");
  line.className = "log-line";
  const time = new Date().toLocaleTimeString();
  line.textContent = `[${time}] ${method} ${url}\n  Authorization: ${headerSent}`;
  requestLog.prepend(line);
}

function showDashboard() {
  loginView.classList.add("hidden");
  dashboardView.classList.remove("hidden");
  sessionStatus.textContent = "Signed in as admin";
  tokenPreview.textContent = getToken();
  loadStudents();
}

function showLogin() {
  dashboardView.classList.add("hidden");
  loginView.classList.remove("hidden");
  sessionStatus.textContent = "Not signed in";
}

// If a token is already saved from a previous session, skip straight
// to the dashboard instead of asking the user to log in again.
if (getToken()) {
  showDashboard();
}

// ---------------------------------------------------------------------
// Login
// ---------------------------------------------------------------------

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const loginError = document.getElementById("loginError");
  loginError.textContent = "";

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    logRequest("POST", "/auth/login", "(none - credentials sent in body)");

    if (!response.ok) {
      const errorBody = await response.json();
      loginError.textContent = errorBody.detail || "Login failed";
      return;
    }

    const data = await response.json();
    saveToken(data.access_token);
    showDashboard();
  } catch (err) {
    loginError.textContent = "Could not reach the server. Is uvicorn running?";
  }
});

document.getElementById("logoutBtn").addEventListener("click", () => {
  clearToken();
  showLogin();
});

// ---------------------------------------------------------------------
// Student CRUD
// ---------------------------------------------------------------------

async function loadStudents() {
  const tableBody = document.getElementById("studentsTableBody");
  const emptyState = document.getElementById("emptyState");
  const authHeader = `Bearer ${getToken()}`;

  const response = await fetch(`${API_BASE}/students`, {
    headers: { Authorization: authHeader },
  });
  logRequest("GET", "/students", authHeader);

  if (response.status === 401) {
    clearToken();
    showLogin();
    return;
  }

  const students = await response.json();
  tableBody.innerHTML = "";

  if (students.length === 0) {
    emptyState.classList.remove("hidden");
  } else {
    emptyState.classList.add("hidden");
  }

  students.forEach((student) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${student.matric_number}</td>
      <td>${student.full_name}</td>
      <td>${student.department}</td>
      <td>${student.faculty}</td>
      <td>${student.level}</td>
      <td><span class="delete-link" data-matric="${student.matric_number}">Remove</span></td>
    `;
    tableBody.appendChild(row);
  });

  // Attach delete handlers after the rows exist in the DOM
  document.querySelectorAll(".delete-link").forEach((link) => {
    link.addEventListener("click", () => deleteStudent(link.dataset.matric));
  });
}

document.getElementById("addStudentForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const addError = document.getElementById("addError");
  addError.textContent = "";

  const payload = {
    full_name: document.getElementById("fullName").value.trim(),
    matric_number: document.getElementById("matricNumber").value.trim(),
    department: document.getElementById("department").value.trim(),
    faculty: document.getElementById("faculty").value.trim(),
    level: document.getElementById("level").value,
  };

  const authHeader = `Bearer ${getToken()}`;

  const response = await fetch(`${API_BASE}/students`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: authHeader,
    },
    body: JSON.stringify(payload),
  });
  logRequest("POST", "/students", authHeader);

  if (!response.ok) {
    const errorBody = await response.json();
    addError.textContent = errorBody.detail || "Could not add student";
    return;
  }

  document.getElementById("addStudentForm").reset();
  loadStudents();
});

async function deleteStudent(matricNumber) {
  const authHeader = `Bearer ${getToken()}`;

  const response = await fetch(`${API_BASE}/students/${encodeURIComponent(matricNumber)}`, {
    method: "DELETE",
    headers: { Authorization: authHeader },
  });
  logRequest("DELETE", `/students/${matricNumber}`, authHeader);

  if (response.status === 401) {
    clearToken();
    showLogin();
    return;
  }

  loadStudents();
}

document.getElementById("refreshBtn").addEventListener("click", loadStudents);
