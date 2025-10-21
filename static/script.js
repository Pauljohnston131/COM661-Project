let token = null;
let currentUser = null;
let isAdmin = false;
let currentPage = 1;
let currentLimit = 10;
let totalPatients = 0;

// Utility Functions
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
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Authentication functions
async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showMessage('Please enter both username and password', 'error');
        return;
    }

    showLoading(true);
    try {
        // Create Basic Auth header
        const authHeader = 'Basic ' + btoa(username + ':' + password);
        
        const response = await fetch('/api/v1.0/login', {
            method: 'GET',
            headers: {
                'Authorization': authHeader
            }
        });

        const data = await response.json();

        if (response.ok) {
            token = data.token;
            currentUser = username;
            
            // Decode token to check admin status
            const tokenData = JSON.parse(atob(token.split('.')[1]));
            isAdmin = tokenData.admin || false;
            
            document.getElementById('current-user').textContent = currentUser;
            document.getElementById('auth-section').style.display = 'none';
            document.getElementById('user-info').style.display = 'block';
            document.getElementById('main-content').style.display = 'block';
            
            // Show/hide admin section based on role
            if (isAdmin) {
                document.getElementById('admin-section').style.display = 'block';
                document.getElementById('admin-indicator').style.display = 'inline';
            } else {
                document.getElementById('admin-section').style.display = 'none';
                document.getElementById('admin-indicator').style.display = 'none';
            }
            
            showMessage('Login successful! Welcome back, ' + username);
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
            await fetch('/api/v1.0/logout', {
                method: 'GET',
                headers: {
                    'x-access-token': token
                }
            });
        } catch (error) {
            console.log('Logout API call failed:', error);
        }
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
    
    // Clear form fields
    document.getElementById('username').value = 'admin';
    document.getElementById('password').value = 'admin123';
    
    showMessage('Logged out successfully');
}

// Patient management functions
async function loadPatients(page = currentPage, limit = currentLimit) {
    if (!token) return;

    showLoading(true);
    try {
        const response = await fetch(`/api/v1.0/patients?page=${page}&limit=${limit}`, {
            headers: {
                'x-access-token': token
            }
        });

        const data = await response.json();

        if (response.ok) {
            displayPatients(data.patients);
            totalPatients = data.count;
            currentPage = page;
            updatePagination();
        } else {
            showMessage(data.error || 'Failed to load patients', 'error');
        }
    } catch (error) {
        showMessage('Failed to load patients: ' + error.message, 'error');
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
                <p>Add your first patient using the form above.</p>
            </div>
        `;
        return;
    }

    patients.forEach(patient => {
        const patientDiv = document.createElement('div');
        patientDiv.className = 'patient-item';
        
        const imageHtml = patient.image_url ? 
            `<img src="${patient.image_url}" alt="${patient.name}" class="patient-image" onerror="this.style.display='none'">` : 
            '<div class="patient-image" style="background: #667eea; color: white; display: flex; align-items: center; justify-content: center; font-size: 1.5em;">👤</div>';
        
        patientDiv.innerHTML = `
            <div class="patient-with-image">
                ${imageHtml}
                <div class="patient-info" style="flex: 1;">
                    <div class="patient-header">
                        <div>
                            <strong>${patient.name}</strong> (${patient.age}, ${patient.gender})<br>
                            <span class="patient-condition">${patient.condition}</span>
                        </div>
                        <span class="patient-id">ID: ${patient._id}</span>
                    </div>
                    <div class="appointment-count">
                        Appointments: ${patient.appointments ? patient.appointments.length : 0}
                    </div>
                    <div class="patient-actions">
                        <button onclick="viewPatientDetails('${patient._id}')">View Details</button>
                        <button onclick="editPatient('${patient._id}')">Edit</button>
                        ${isAdmin ? `<button onclick="deletePatient('${patient._id}')" class="danger-btn">Delete</button>` : ''}
                    </div>
                </div>
            </div>
        `;
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

function changePage(direction) {
    const newPage = currentPage + direction;
    if (newPage >= 1) {
        loadPatients(newPage);
    }
}

async function addPatient() {
    if (!token) return;

    const name = document.getElementById('patient-name').value;
    const age = document.getElementById('patient-age').value;
    const gender = document.getElementById('patient-gender').value;
    const condition = document.getElementById('patient-condition').value;
    const imageUrl = document.getElementById('patient-image').value;

    if (!name || !age || !gender || !condition) {
        showMessage('Please fill in all required fields', 'error');
        return;
    }

    if (age < 0 || age > 120) {
        showMessage('Age must be between 0 and 120', 'error');
        return;
    }

    showLoading(true);
    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('age', age);
        formData.append('gender', gender);
        formData.append('condition', condition);
        if (imageUrl) formData.append('image_url', imageUrl);

        const response = await fetch('/api/v1.0/patients', {
            method: 'POST',
            headers: {
                'x-access-token': token
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('Patient added successfully!');
            clearPatientForm();
            await loadPatients(currentPage);
        } else {
            showMessage(data.error || 'Failed to add patient', 'error');
        }
    } catch (error) {
        showMessage('Failed to add patient: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function clearPatientForm() {
    document.getElementById('patient-name').value = '';
    document.getElementById('patient-age').value = '';
    document.getElementById('patient-gender').value = '';
    document.getElementById('patient-condition').value = '';
    document.getElementById('patient-image').value = '';
}

function clearAllForms() {
    clearPatientForm();
    clearAppointmentForm();
    document.getElementById('search-query').value = '';
    document.getElementById('view-patient-id').value = '';
    showMessage('All forms cleared', 'success');
}

async function deletePatient(patientId) {
    if (!token || !isAdmin) {
        showMessage('Admin access required to delete patients', 'error');
        return;
    }

    if (!confirm('Are you sure you want to delete this patient? This action cannot be undone.')) return;

    showLoading(true);
    try {
        const response = await fetch(`/api/v1.0/patients/${patientId}`, {
            method: 'DELETE',
            headers: {
                'x-access-token': token
            }
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('Patient deleted successfully!');
            await loadPatients(currentPage);
        } else {
            showMessage(data.error || 'Failed to delete patient', 'error');
        }
    } catch (error) {
        showMessage('Failed to delete patient: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function viewPatientDetails(patientId) {
    showLoading(true);
    try {
        const response = await fetch(`/api/v1.0/patients/${patientId}`, {
            headers: {
                'x-access-token': token
            }
        });

        const patient = await response.json();

        if (response.ok) {
            displayPatientDetails(patient);
        } else {
            showMessage(patient.error || 'Failed to load patient details', 'error');
        }
    } catch (error) {
        showMessage('Failed to load patient details: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayPatientDetails(patient) {
    const container = document.getElementById('patient-details-content');
    
    const appointmentsHtml = patient.appointments && patient.appointments.length > 0 ? 
        patient.appointments.map(apt => `
            <div class="appointment-details">
                <p><strong>Dr. ${apt.doctor}</strong> - <span class="status-${apt.status.toLowerCase()}">${apt.status}</span></p>
                <p>Date: ${formatDate(apt.date)}</p>
                <p>Notes: ${apt.notes}</p>
                <p>Appointment ID: <span class="patient-id">${apt._id}</span></p>
            </div>
        `).join('') : 
        '<p>No appointments scheduled.</p>';

    container.innerHTML = `
        <div class="patient-details-grid">
            <div class="form-group">
                <label>Name:</label>
                <p><strong>${patient.name}</strong></p>
            </div>
            <div class="form-group">
                <label>Age:</label>
                <p>${patient.age}</p>
            </div>
            <div class="form-group">
                <label>Gender:</label>
                <p>${patient.gender}</p>
            </div>
            <div class="form-group">
                <label>Condition:</label>
                <p>${patient.condition}</p>
            </div>
            <div class="form-group">
                <label>Patient ID:</label>
                <p class="patient-id">${patient._id}</p>
            </div>
            ${patient.image_url ? `
            <div class="form-group">
                <label>Photo:</label>
                <img src="${patient.image_url}" alt="${patient.name}" style="max-width: 200px; border-radius: 8px;" onerror="this.style.display='none'">
            </div>` : ''}
        </div>
        
        <div class="form-group">
            <label>Appointments (${patient.appointments ? patient.appointments.length : 0}):</label>
            ${appointmentsHtml}
        </div>
        
        <div class="form-actions">
            <button onclick="closeModal('patient-details-modal')">Close</button>
            <button onclick="editPatient('${patient._id}')">Edit Patient</button>
        </div>
    `;
    
    openModal('patient-details-modal');
}

async function editPatient(patientId) {
    showLoading(true);
    try {
        const response = await fetch(`/api/v1.0/patients/${patientId}`, {
            headers: {
                'x-access-token': token
            }
        });

        const patient = await response.json();

        if (response.ok) {
            displayEditPatientForm(patient);
        } else {
            showMessage(patient.error || 'Failed to load patient for editing', 'error');
        }
    } catch (error) {
        showMessage('Failed to load patient for editing: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayEditPatientForm(patient) {
    const container = document.getElementById('edit-patient-content');
    
    container.innerHTML = `
        <form onsubmit="updatePatient('${patient._id}'); return false;">
            <div class="form-group">
                <label for="edit-name">Name:</label>
                <input type="text" id="edit-name" value="${patient.name}" required>
            </div>
            <div class="form-group">
                <label for="edit-age">Age:</label>
                <input type="number" id="edit-age" value="${patient.age}" min="0" max="120" required>
            </div>
            <div class="form-group">
                <label for="edit-gender">Gender:</label>
                <select id="edit-gender" required>
                    <option value="Male" ${patient.gender === 'Male' ? 'selected' : ''}>Male</option>
                    <option value="Female" ${patient.gender === 'Female' ? 'selected' : ''}>Female</option>
                    <option value="Other" ${patient.gender === 'Other' ? 'selected' : ''}>Other</option>
                </select>
            </div>
            <div class="form-group">
                <label for="edit-condition">Condition:</label>
                <input type="text" id="edit-condition" value="${patient.condition}" required>
            </div>
            <div class="form-group">
                <label for="edit-image">Image URL:</label>
                <input type="text" id="edit-image" value="${patient.image_url || ''}">
            </div>
            <div class="form-actions">
                <button type="button" onclick="closeModal('edit-patient-modal')">Cancel</button>
                <button type="submit">Update Patient</button>
            </div>
        </form>
    `;
    
    openModal('edit-patient-modal');
}

async function updatePatient(patientId) {
    const name = document.getElementById('edit-name').value;
    const age = document.getElementById('edit-age').value;
    const gender = document.getElementById('edit-gender').value;
    const condition = document.getElementById('edit-condition').value;
    const imageUrl = document.getElementById('edit-image').value;

    if (!name || !age || !gender || !condition) {
        showMessage('Please fill in all required fields', 'error');
        return;
    }

    showLoading(true);
    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('age', age);
        formData.append('gender', gender);
        formData.append('condition', condition);
        if (imageUrl) formData.append('image_url', imageUrl);

        const response = await fetch(`/api/v1.0/patients/${patientId}`, {
            method: 'PUT',
            headers: {
                'x-access-token': token
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('Patient updated successfully!');
            closeModal('edit-patient-modal');
            await loadPatients(currentPage);
        } else {
            showMessage(data.error || 'Failed to update patient', 'error');
        }
    } catch (error) {
        showMessage('Failed to update patient: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Search functionality
async function searchPatients() {
    const query = document.getElementById('search-query').value.trim();
    if (!query) {
        showMessage('Please enter a search term', 'warning');
        return;
    }

    showLoading(true);
    try {
        const response = await fetch(`/api/v1.0/search?q=${encodeURIComponent(query)}`, {
            headers: {
                'x-access-token': token
            }
        });

        const data = await response.json();

        if (response.ok) {
            displayPatients(data.results);
            document.getElementById('patients-count').textContent = `${data.results.length} search results`;
            
            // Reset pagination for search results
            currentPage = 1;
            updatePagination();
            
            if (data.results.length === 0) {
                showMessage('No patients found matching your search', 'warning');
            } else {
                showMessage(`Found ${data.results.length} patients matching "${query}"`);
            }
        } else {
            showMessage(data.error || 'Search failed', 'error');
        }
    } catch (error) {
        showMessage('Search failed: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function clearSearch() {
    document.getElementById('search-query').value = '';
    loadPatients(1);
    showMessage('Search cleared', 'success');
}

// Appointment management functions
async function addAppointment() {
    if (!token) return;

    const patientId = document.getElementById('appointment-patient-id').value.trim();
    const doctor = document.getElementById('appointment-doctor').value;
    const date = document.getElementById('appointment-date').value;
    const notes = document.getElementById('appointment-notes').value;
    const status = document.getElementById('appointment-status').value;

    if (!patientId || !doctor || !date || !notes) {
        showMessage('Please fill in all appointment fields', 'error');
        return;
    }

    showLoading(true);
    try {
        const formData = new FormData();
        formData.append('doctor', doctor);
        formData.append('date', date);
        formData.append('notes', notes);
        formData.append('status', status);

        const response = await fetch(`/api/v1.0/patients/${patientId}/appointments`, {
            method: 'POST',
            headers: {
                'x-access-token': token
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('Appointment added successfully!');
            clearAppointmentForm();
            // Refresh appointments if viewing this patient's appointments
            if (document.getElementById('view-patient-id').value === patientId) {
                await viewAppointments();
            }
            await loadPatients(currentPage);
        } else {
            showMessage(data.error || 'Failed to add appointment', 'error');
        }
    } catch (error) {
        showMessage('Failed to add appointment: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function clearAppointmentForm() {
    document.getElementById('appointment-doctor').value = '';
    document.getElementById('appointment-date').value = '';
    document.getElementById('appointment-notes').value = '';
    document.getElementById('appointment-status').value = 'Scheduled';
}

async function viewAppointments() {
    if (!token) return;

    const patientId = document.getElementById('view-patient-id').value.trim();
    if (!patientId) {
        showMessage('Please enter a Patient ID', 'error');
        return;
    }

    showLoading(true);
    try {
        const response = await fetch(`/api/v1.0/patients/${patientId}/appointments`, {
            headers: {
                'x-access-token': token
            }
        });

        const data = await response.json();

        if (response.ok) {
            displayAppointments(data.appointments, patientId);
        } else {
            showMessage(data.error || 'Failed to load appointments', 'error');
        }
    } catch (error) {
        showMessage('Failed to load appointments: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayAppointments(appointments, patientId) {
    const container = document.getElementById('appointments-list');
    container.innerHTML = '';

    if (!appointments || appointments.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div>📅</div>
                <p>No appointments found for this patient.</p>
            </div>
        `;
        return;
    }

    appointments.forEach(appointment => {
        const appointmentDiv = document.createElement('div');
        appointmentDiv.className = 'appointment-item';
        appointmentDiv.innerHTML = `
            <div class="appointment-header">
                <div class="appointment-info">
                    <strong>Dr. ${appointment.doctor}</strong><br>
                    <span class="appointment-date">${formatDate(appointment.date)}</span><br>
                    Status: <span class="status-${appointment.status.toLowerCase()}">${appointment.status}</span>
                </div>
                <span class="appointment-id">ID: ${appointment._id}</span>
            </div>
            <div class="appointment-details">
                <p><strong>Notes:</strong> ${appointment.notes}</p>
            </div>
            <div class="appointment-actions">
                ${isAdmin ? `<button onclick="deleteAppointment('${patientId}', '${appointment._id}')" class="danger-btn">Delete</button>` : ''}
            </div>
        `;
        container.appendChild(appointmentDiv);
    });

    showMessage(`Found ${appointments.length} appointments for patient ${patientId}`);
}

async function deleteAppointment(patientId, appointmentId) {
    if (!token || !isAdmin) {
        showMessage('Admin access required to delete appointments', 'error');
        return;
    }

    if (!confirm('Are you sure you want to delete this appointment?')) return;

    showLoading(true);
    try {
        const response = await fetch(`/api/v1.0/patients/${patientId}/appointments/${appointmentId}`, {
            method: 'DELETE',
            headers: {
                'x-access-token': token
            }
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('Appointment deleted successfully!');
            await viewAppointments();
            await loadPatients(currentPage);
        } else {
            showMessage(data.error || 'Failed to delete appointment', 'error');
        }
    } catch (error) {
        showMessage('Failed to delete appointment: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Admin functions
async function systemStats() {
    if (!token || !isAdmin) {
        showMessage('Admin access required', 'error');
        return;
    }

    showLoading(true);
    try {
        const patientsResponse = await fetch('/api/v1.0/patients?limit=1000', {
            headers: {
                'x-access-token': token
            }
        });
        
        const patientsData = await patientsResponse.json();
        
        if (patientsResponse.ok) {
            let totalAppointments = 0;
            let scheduledAppointments = 0;
            let completedAppointments = 0;
            let cancelledAppointments = 0;

            patientsData.patients.forEach(patient => {
                if (patient.appointments) {
                    totalAppointments += patient.appointments.length;
                    patient.appointments.forEach(apt => {
                        if (apt.status === 'Scheduled') scheduledAppointments++;
                        if (apt.status === 'Completed') completedAppointments++;
                        if (apt.status === 'Cancelled') cancelledAppointments++;
                    });
                }
            });
            
            document.getElementById('stats-content').innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-number">${patientsData.patients.length}</span>
                        <span class="stat-label">Total Patients</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">${totalAppointments}</span>
                        <span class="stat-label">Total Appointments</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">${scheduledAppointments}</span>
                        <span class="stat-label">Scheduled</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">${completedAppointments}</span>
                        <span class="stat-label">Completed</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-number">${cancelledAppointments}</span>
                        <span class="stat-label">Cancelled</span>
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <h4>System Information</h4>
                    <p><strong>Current User:</strong> ${currentUser} ${isAdmin ? '(Administrator)' : '(User)'}</p>
                    <p><strong>Default Admin:</strong> admin/admin123</p>
                    <p><strong>API Version:</strong> 1.0</p>
                </div>
            `;
            openModal('stats-modal');
        }
    } catch (error) {
        showMessage('Failed to load stats: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function loadAppointmentStats() {
    if (!token || !isAdmin) {
        showMessage('Admin access required', 'error');
        return;
    }

    showLoading(true);
    try {
        const response = await fetch('/api/v1.0/stats/appointments', {
            headers: {
                'x-access-token': token
            }
        });

        const stats = await response.json();

        if (response.ok) {
            let statsHtml = '<h4>Appointments per Doctor</h4>';
            if (stats.length > 0) {
                statsHtml += '<ul style="list-style: none; padding: 0;">';
                stats.forEach(stat => {
                    statsHtml += `<li style="padding: 8px; border-bottom: 1px solid #eee;">
                        <strong>${stat._id}</strong>: ${stat.count} appointment(s)
                    </li>`;
                });
                statsHtml += '</ul>';
            } else {
                statsHtml += '<p>No appointment statistics available.</p>';
            }
            
            document.getElementById('stats-content').innerHTML = statsHtml;
            openModal('stats-modal');
        } else {
            showMessage('Failed to load appointment statistics', 'error');
        }
    } catch (error) {
        showMessage('Failed to load appointment statistics: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Quick fill helpers for testing
function quickFillPatient() {
    const names = ['John Smith', 'Maria Garcia', 'David Johnson', 'Sarah Williams', 'James Brown'];
    const conditions = ['Hypertension', 'Diabetes', 'Asthma', 'Arthritis', 'Migraine'];
    
    document.getElementById('patient-name').value = names[Math.floor(Math.random() * names.length)];
    document.getElementById('patient-age').value = Math.floor(Math.random() * 80) + 20;
    document.getElementById('patient-gender').value = ['Male', 'Female'][Math.floor(Math.random() * 2)];
    document.getElementById('patient-condition').value = conditions[Math.floor(Math.random() * conditions.length)];
    document.getElementById('patient-image').value = 'https://via.placeholder.com/150/667eea/ffffff?text=Patient';
    
    showMessage('Patient form filled with sample data', 'success');
}

function quickFillAppointment() {
    const doctors = ['Smith', 'Johnson', 'Williams', 'Brown', 'Davis'];
    const notes = ['Routine checkup', 'Follow-up visit', 'Consultation', 'Emergency visit', 'Specialist referral'];
    
    // Set a date for tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(10, 0, 0, 0);
    
    document.getElementById('appointment-doctor').value = `Dr. ${doctors[Math.floor(Math.random() * doctors.length)]}`;
    document.getElementById('appointment-date').value = tomorrow.toISOString().slice(0, 16);
    document.getElementById('appointment-notes').value = notes[Math.floor(Math.random() * notes.length)];
    document.getElementById('appointment-status').value = 'Scheduled';
    
    showMessage('Appointment form filled with sample data', 'success');
}

async function generateSampleData() {
    if (!token || !isAdmin) {
        showMessage('Admin access required', 'error');
        return;
    }

    showMessage('Generating sample data...', 'success');
    
    // Generate 3 sample patients
    const samplePatients = [
        { name: 'Alice Johnson', age: 45, gender: 'Female', condition: 'Hypertension' },
        { name: 'Bob Wilson', age: 62, gender: 'Male', condition: 'Diabetes' },
        { name: 'Carol Davis', age: 38, gender: 'Female', condition: 'Asthma' }
    ];

    for (const patient of samplePatients) {
        try {
            const formData = new FormData();
            formData.append('name', patient.name);
            formData.append('age', patient.age);
            formData.append('gender', patient.gender);
            formData.append('condition', patient.condition);

            await fetch('/api/v1.0/patients', {
                method: 'POST',
                headers: {
                    'x-access-token': token
                },
                body: formData
            });
        } catch (error) {
            console.error('Failed to create sample patient:', error);
        }
    }

    await loadPatients(1);
    showMessage('Sample data generated successfully!', 'success');
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Ctrl + L to focus search
    if (event.ctrlKey && event.key === 'l') {
        event.preventDefault();
        document.getElementById('search-query').focus();
    }
    
    // Escape to close modals
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (modal.style.display === 'block') {
                modal.style.display = 'none';
            }
        });
    }
});

// Auto-focus username field on page load
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('username').focus();
    
    // Set minimum datetime for appointment date to current time
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('appointment-date').min = now.toISOString().slice(0, 16);
});

// Export functions for global access
window.login = login;
window.logout = logout;
window.addPatient = addPatient;
window.loadPatients = loadPatients;
window.deletePatient = deletePatient;
window.viewPatientDetails = viewPatientDetails;
window.editPatient = editPatient;
window.updatePatient = updatePatient;
window.addAppointment = addAppointment;
window.viewAppointments = viewAppointments;
window.deleteAppointment = deleteAppointment;
window.searchPatients = searchPatients;
window.clearSearch = clearSearch;
window.systemStats = systemStats;
window.loadAppointmentStats = loadAppointmentStats;
window.quickFillPatient = quickFillPatient;
window.quickFillAppointment = quickFillAppointment;
window.generateSampleData = generateSampleData;
window.clearPatientForm = clearPatientForm;
window.clearAppointmentForm = clearAppointmentForm;
window.clearAllForms = clearAllForms;
window.closeModal = closeModal;
window.changePage = changePage;