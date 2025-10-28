let token = null;
let currentUser = null;
let isAdmin = false;
let currentPage = 1;
let currentLimit = 10;
let totalPatients = 0;

// ------------------------------
// Utility Functions
// ------------------------------
function showMessage(message, type = 'success') {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    messageDiv.style.opacity = '1';
    setTimeout(() => {
        messageDiv.style.opacity = '0';
    }, 5000);
}

function showLoading(show = true) {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = show ? 'flex' : 'none';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function formatDate(dateString) {
    if (!dateString || dateString === 'Unknown') return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-GB', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ------------------------------
// Authentication
// ------------------------------
async function login() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    if (!username || !password) {
        showMessage('Please enter both username and password', 'error');
        return;
    }

    showLoading(true);
    try {
        const authHeader = 'Basic ' + btoa(username + ':' + password);
        const response = await fetch('/api/v1.0/auth/login', {
            method: 'GET',
            headers: { 'Authorization': authHeader }
        });

        const data = await response.json();

        if (response.ok) {
            token = data.token;
            currentUser = username;
            const tokenData = JSON.parse(atob(token.split('.')[1]));
            isAdmin = tokenData.admin || false;

            document.getElementById('current-user').textContent = currentUser;
            document.getElementById('auth-section').style.display = 'none';
            document.getElementById('user-info').style.display = 'block';
            document.getElementById('main-content').style.display = 'block';
            if (isAdmin) {
                document.getElementById('admin-section').style.display = 'block';
                document.getElementById('admin-indicator').style.display = 'inline';
            } else {
                document.getElementById('admin-section').style.display = 'none';
                document.getElementById('admin-indicator').style.display = 'none';
            }

            showMessage(`Welcome back, ${username}`);
            await loadPatients();
        } else {
            showMessage(data.error || 'Login failed', 'error');
        }
    } catch (error) {
        showMessage('Login failed: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function logout() {
    if (token) {
        try {
            await fetch('/api/v1.0/auth/logout', {
                method: 'GET',
                headers: { 'x-access-token': token }
            });
        } catch (err) {}
    }
    token = null;
    currentUser = null;
    isAdmin = false;

    document.getElementById('user-info').style.display = 'none';
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-content').style.display = 'none';
    document.getElementById('admin-section').style.display = 'none';
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('admin-indicator').style.display = 'none';
    document.getElementById('username').value = 'admin';
    document.getElementById('password').value = 'admin123';

    showMessage('Logged out successfully');
}

// ------------------------------
// Patient Management
// ------------------------------
async function loadPatients(page = currentPage, limit = currentLimit) {
    if (!token) return;
    showLoading(true);
    try {
        const res = await fetch(`/api/v1.0/patients?page=${page}&limit=${limit}`, {
            headers: { 'x-access-token': token }
        });
        const data = await res.json();
        if (res.ok) {
            displayPatients(data.patients);
            totalPatients = data.count;
            currentPage = page;
            updatePagination();
        } else showMessage(data.error, 'error');
    } catch (err) {
        showMessage('Failed to load patients: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayPatients(patients) {
    const container = document.getElementById('patients-list');
    const countBadge = document.getElementById('patients-count');
    container.innerHTML = '';
    countBadge.textContent = `${patients.length} patients`;

    if (patients.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div>📝</div>
                <p>No patients found.</p>
            </div>`;
        return;
    }

    patients.forEach(p => {
        const pid = p.id || p._id;
        const imageHtml = p.image_url
            ? `<img src="${p.image_url}" alt="${p.name}" class="patient-image" onerror="this.style.display='none'">`
            : '<div class="patient-image" style="background:#667eea;color:white;display:flex;align-items:center;justify-content:center;font-size:1.5em;">👤</div>';
        const patientDiv = document.createElement('div');
        patientDiv.className = 'patient-item';
        patientDiv.innerHTML = `
            <div class="patient-with-image">
                ${imageHtml}
                <div class="patient-info">
                    <div class="patient-header">
                        <div>
                            <strong>${p.name || 'Unnamed'}</strong> (${p.age})
                            <br><span class="patient-condition">${p.condition || 'N/A'}</span>
                        </div>
                        <span class="patient-id">ID: ${pid}</span>
                    </div>
                    <div class="appointment-count">Appointments: ${p.appointments?.length || 0}</div>
                    <div class="patient-actions">
                        <button onclick="viewPatientDetails('${pid}')">View</button>
                        <button onclick="editPatient('${pid}')">Edit</button>
                        ${isAdmin ? `<button onclick="deletePatient('${pid}')" class="danger-btn">Delete</button>` : ''}
                    </div>
                </div>
            </div>`;
        container.appendChild(patientDiv);
    });
}

function updatePagination() {
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const totalPages = Math.ceil(totalPatients / currentLimit);
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
}

function changePage(dir) {
    const newPage = currentPage + dir;
    if (newPage >= 1) loadPatients(newPage);
}

async function addPatient() {
    const name = document.getElementById('patient-name').value.trim();
    const age = document.getElementById('patient-age').value.trim();
    const condition = document.getElementById('patient-condition').value.trim();
    const imageUrl = document.getElementById('patient-image').value.trim();
    if (!name || !age || !condition) {
        showMessage('Please fill in all required fields', 'error');
        return;
    }
    showLoading(true);
    try {
        const fd = new FormData();
        fd.append('name', name);
        fd.append('age', age);
        fd.append('condition', condition);
        if (imageUrl) fd.append('image_url', imageUrl);
        const res = await fetch('/api/v1.0/patients', {
            method: 'POST',
            headers: { 'x-access-token': token },
            body: fd
        });
        const data = await res.json();
        if (res.ok) {
            showMessage('Patient added successfully!');
            clearPatientForm();
            await loadPatients(currentPage);
        } else showMessage(data.error, 'error');
    } catch (err) {
        showMessage('Failed: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

function clearPatientForm() {
    document.getElementById('patient-name').value = '';
    document.getElementById('patient-age').value = '';
    document.getElementById('patient-condition').value = '';
    document.getElementById('patient-image').value = '';
}

async function deletePatient(id) {
    if (!isAdmin) {
        showMessage('Admin access required', 'error');
        return;
    }
    if (!confirm('Delete this patient?')) return;
    showLoading(true);
    try {
        const res = await fetch(`/api/v1.0/patients/${id}`, {
            method: 'DELETE',
            headers: { 'x-access-token': token }
        });
        const data = await res.json();
        if (res.ok) {
            showMessage('Patient deleted');
            await loadPatients();
        } else showMessage(data.error, 'error');
    } catch (err) {
        showMessage('Error: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function viewPatientDetails(id) {
    showLoading(true);
    try {
        const res = await fetch(`/api/v1.0/patients/${id}`, {
            headers: { 'x-access-token': token }
        });
        const patient = await res.json();
        if (res.ok) displayPatientDetails(patient);
        else showMessage(patient.error, 'error');
    } catch (err) {
        showMessage('Error: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayPatientDetails(p) {
    const pid = p.id || p._id;
    const container = document.getElementById('patient-details-content');
    const appts = p.appointments && p.appointments.length > 0
        ? p.appointments.map(a => `
            <div class="appointment-details">
                <p><strong>${a.doctor}</strong> - <span class="status-${a.status.toLowerCase()}">${a.status}</span></p>
                <p>Date: ${formatDate(a.date)}</p>
                <p>Notes: ${a.notes}</p>
                <p>Appointment ID: ${a._id}</p>
            </div>`).join('')
        : '<p>No appointments scheduled.</p>';

    container.innerHTML = `
        <div class="patient-details-grid">
            <p><strong>${p.name}</strong></p>
            <p>Age: ${p.age}</p>
            <p>Condition: ${p.condition}</p>
            <p>ID: <span class="patient-id">${pid}</span> 
                <button onclick="navigator.clipboard.writeText('${pid}')">Copy ID</button>
            </p>
            ${p.image_url ? `<img src="${p.image_url}" alt="${p.name}" style="max-width:200px;border-radius:8px;" onerror="this.style.display='none'">` : ''}
        </div>
        <div><h4>Appointments (${p.appointments?.length || 0}):</h4>${appts}</div>
        <div class="form-actions">
            <button onclick="closeModal('patient-details-modal')">Close</button>
            <button onclick="editPatient('${pid}')">Edit</button>
        </div>`;
    openModal('patient-details-modal');
}

async function editPatient(id) {
    showLoading(true);
    try {
        const res = await fetch(`/api/v1.0/patients/${id}`, { headers: { 'x-access-token': token } });
        const p = await res.json();
        if (res.ok) displayEditPatientForm(p);
        else showMessage(p.error, 'error');
    } catch (err) {
        showMessage('Error: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayEditPatientForm(p) {
    const pid = p.id || p._id;
    const container = document.getElementById('edit-patient-content');
    container.innerHTML = `
        <form onsubmit="updatePatient('${pid}'); return false;">
            <label>Name:</label><input id="edit-name" value="${p.name}" required>
            <label>Age:</label><input id="edit-age" type="number" value="${p.age}" min="0" max="120" required>
            <label>Condition:</label><input id="edit-condition" value="${p.condition}" required>
            <label>Image URL:</label><input id="edit-image" value="${p.image_url || ''}">
            <div class="form-actions">
                <button type="button" onclick="closeModal('edit-patient-modal')">Cancel</button>
                <button type="submit">Update</button>
            </div>
        </form>`;
    openModal('edit-patient-modal');
}

async function updatePatient(id) {
    const name = document.getElementById('edit-name').value.trim();
    const age = document.getElementById('edit-age').value.trim();
    const condition = document.getElementById('edit-condition').value.trim();
    const image = document.getElementById('edit-image').value.trim();
    if (!name || !age || !condition) {
        showMessage('All fields required', 'error');
        return;
    }
    showLoading(true);
    try {
        const fd = new FormData();
        fd.append('name', name);
        fd.append('age', age);
        fd.append('condition', condition);
        if (image) fd.append('image_url', image);
        const res = await fetch(`/api/v1.0/patients/${id}`, {
            method: 'PUT',
            headers: { 'x-access-token': token },
            body: fd
        });
        const data = await res.json();
        if (res.ok) {
            showMessage('Patient updated');
            closeModal('edit-patient-modal');
            await loadPatients();
        } else showMessage(data.error, 'error');
    } catch (err) {
        showMessage('Error: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ------------------------------
// Search
// ------------------------------
async function searchPatients() {
    const q = document.getElementById('search-query').value.trim();
    if (!q) {
        showMessage('Enter search term', 'warning');
        return;
    }
    showLoading(true);
    try {
        const res = await fetch(`/api/v1.0/search?q=${encodeURIComponent(q)}`, {
            headers: { 'x-access-token': token }
        });
        const data = await res.json();
        if (res.ok) {
            displayPatients(data.results);
            showMessage(`Found ${data.results.length} results`);
        } else showMessage(data.error, 'error');
    } catch (err) {
        showMessage('Error: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

function clearSearch() {
    document.getElementById('search-query').value = '';
    loadPatients(1);
    showMessage('Search cleared');
}

// ------------------------------
// Appointments
// ------------------------------
async function addAppointment() {
    const patientId = document.getElementById('appointment-patient-id').value.trim();
    const doctor = document.getElementById('appointment-doctor').value.trim();
    const date = document.getElementById('appointment-date').value;
    const notes = document.getElementById('appointment-notes').value.trim();
    const status = document.getElementById('appointment-status').value;
    if (!patientId || !doctor || !date || !notes) {
        showMessage('Fill all fields', 'error');
        return;
    }
    showLoading(true);
    try {
        const fd = new FormData();
        fd.append('doctor', doctor);
        fd.append('date', date);
        fd.append('notes', notes);
        fd.append('status', status);
        const res = await fetch(`/api/v1.0/patients/${patientId}/appointments`, {
            method: 'POST',
            headers: { 'x-access-token': token },
            body: fd
        });
        const data = await res.json();
        if (res.ok) {
            showMessage('Appointment added');
            clearAppointmentForm();
            await viewAppointments();
        } else showMessage(data.error, 'error');
    } catch (err) {
        showMessage('Error: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

function clearAppointmentForm() {
    document.getElementById('appointment-patient-id').value = '';
    document.getElementById('appointment-doctor').value = '';
    document.getElementById('appointment-date').value = '';
    document.getElementById('appointment-notes').value = '';
    document.getElementById('appointment-status').value = 'Scheduled';
}

async function viewAppointments() {
    const pid = document.getElementById('view-patient-id').value.trim();
    if (!pid) {
        showMessage('Enter patient ID', 'error');
        return;
    }
    showLoading(true);
    try {
        const res = await fetch(`/api/v1.0/patients/${pid}/appointments`, {
            headers: { 'x-access-token': token }
        });
        const data = await res.json();
        if (res.ok) displayAppointments(data.appointments, pid);
        else showMessage(data.error, 'error');
    } catch (err) {
        showMessage('Error: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayAppointments(appts, pid) {
    const container = document.getElementById('appointments-list');
    container.innerHTML = '';
    if (!appts || appts.length === 0) {
        container.innerHTML = `<div class="empty-state">📅 No appointments found.</div>`;
        return;
    }
    appts.forEach(a => {
        const aid = a._id || a.id;
        const div = document.createElement('div');
        div.className = 'appointment-item';
        div.innerHTML = `
            <strong>${a.doctor}</strong> - ${formatDate(a.date)} (${a.status})
            <p>${a.notes}</p>
            <p>ID: ${aid}</p>
            ${isAdmin ? `<button onclick="deleteAppointment('${pid}','${aid}')" class="danger-btn">Delete</button>` : ''}
        `;
        container.appendChild(div);
    });
}

async function deleteAppointment(pid, aid) {
    if (!isAdmin) {
        showMessage('Admin required', 'error');
        return;
    }
    if (!confirm('Delete this appointment?')) return;
    showLoading(true);
    try {
        const res = await fetch(`/api/v1.0/patients/${pid}/appointments/${aid}`, {
            method: 'DELETE',
            headers: { 'x-access-token': token }
        });
        const data = await res.json();
        if (res.ok) {
            showMessage('Appointment deleted');
            await viewAppointments();
        } else showMessage(data.error, 'error');
    } catch (err) {
        showMessage('Error: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ------------------------------
// Admin Stats
// ------------------------------
async function systemStats() {
    if (!isAdmin) {
        showMessage('Admin only', 'error');
        return;
    }
    showLoading(true);
    try {
        const res = await fetch('/api/v1.0/patients?limit=1000', {
            headers: { 'x-access-token': token }
        });
        const data = await res.json();
        if (res.ok) {
            let total = 0;
            data.patients.forEach(p => { total += p.appointments?.length || 0; });
            document.getElementById('stats-content').innerHTML = `
                <h4>System Stats</h4>
                <p><strong>Patients:</strong> ${data.patients.length}</p>
                <p><strong>Total Appointments:</strong> ${total}</p>
                <p><strong>Current User:</strong> ${currentUser} (${isAdmin ? 'Admin' : 'User'})</p>
            `;
            openModal('stats-modal');
        }
    } catch (err) {
        showMessage('Error: ' + err.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ------------------------------
// Helpers
// ------------------------------
function quickFillPatient() {
    const names = ['John Smith', 'Maria Garcia', 'David Johnson', 'Sarah Williams', 'James Brown'];
    const conditions = ['Hypertension', 'Diabetes', 'Asthma', 'Arthritis', 'Migraine'];
    document.getElementById('patient-name').value = names[Math.floor(Math.random() * names.length)];
    document.getElementById('patient-age').value = Math.floor(Math.random() * 80) + 20;
    document.getElementById('patient-condition').value = conditions[Math.floor(Math.random() * conditions.length)];
    document.getElementById('patient-image').value = 'https://via.placeholder.com/150/667eea/ffffff?text=Patient';
    showMessage('Patient form filled', 'success');
}

function quickFillAppointment() {
    const docs = ['Dr. Smith', 'Dr. Johnson', 'Dr. Lee', 'Dr. Brown', 'Dr. Davis'];
    const notes = ['Routine checkup', 'Consultation', 'Follow-up', 'Emergency', 'Referral'];
    const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
    document.getElementById('appointment-doctor').value = docs[Math.floor(Math.random() * docs.length)];
    document.getElementById('appointment-date').value = tomorrow.toISOString().slice(0, 16);
    document.getElementById('appointment-notes').value = notes[Math.floor(Math.random() * notes.length)];
    document.getElementById('appointment-status').value = 'Scheduled';
    showMessage('Appointment form filled', 'success');
}

function clearAllForms() {
    clearPatientForm();
    clearAppointmentForm();
    document.getElementById('search-query').value = '';
    document.getElementById('view-patient-id').value = '';
    showMessage('Forms cleared');
}

// ------------------------------
// Init
// ------------------------------
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('username').focus();
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('appointment-date').min = now.toISOString().slice(0, 16);
});
