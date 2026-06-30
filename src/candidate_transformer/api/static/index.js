document.addEventListener('DOMContentLoaded', () => {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        const dropArea = input.closest('.file-drop-area');
        const span = dropArea.querySelector('span');
        const originalText = span.textContent;
        
        input.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                dropArea.classList.add('has-file');
                span.textContent = e.target.files[0].name;
            } else {
                dropArea.classList.remove('has-file');
                span.textContent = originalText;
            }
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            input.addEventListener(eventName, () => dropArea.classList.add('active'));
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            input.addEventListener(eventName, () => dropArea.classList.remove('active'));
        });
    });

    const form = document.getElementById('transform-form');
    const resetBtn = document.getElementById('reset-btn');
    const overlay = document.getElementById('loading-overlay');
    const resultsSection = document.getElementById('results-section');
    const candidatesContainer = document.getElementById('candidates-container');
    const metricsContainer = document.getElementById('metrics-container');

    resetBtn.addEventListener('click', () => {
        form.reset();
        fileInputs.forEach(input => {
            const dropArea = input.closest('.file-drop-area');
            const span = dropArea.querySelector('span');
            dropArea.classList.remove('has-file');
            
            // Reset to original text based on the ID
            if (input.id === 'resume') span.textContent = 'Resume (PDF)';
            else if (input.id === 'csv') span.textContent = 'Recruiter CSV';
            else if (input.id === 'ats_json') span.textContent = 'ATS JSON';
            else if (input.id === 'github_json') span.textContent = 'GitHub JSON';
            else if (input.id === 'notes') span.textContent = 'Recruiter Notes';
        });
        resultsSection.classList.add('hidden');
        candidatesContainer.innerHTML = '';
        metricsContainer.innerHTML = '';
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        let hasFile = false;
        fileInputs.forEach(input => {
            if (input.files.length > 0) hasFile = true;
        });
        
        if (!hasFile) {
            alert("Please select at least one file to transform.");
            return;
        }

        const formData = new FormData(form);
        
        overlay.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        
        try {
            const response = await fetch('/transform', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                renderResults(data);
            } else {
                alert(`Error: ${data.detail || 'Failed to process files'}`);
            }
        } catch (error) {
            alert(`Error connecting to server: ${error.message}`);
        } finally {
            overlay.classList.add('hidden');
        }
    });

    function renderResults(data) {
        // Render Metrics
        metricsContainer.innerHTML = `
            <div class="metric-badge">Parsing Time: <span>${data.metrics.parsing_time_ms.toFixed(1)}ms</span></div>
            <div class="metric-badge">Pipeline Duration: <span>${data.metrics.pipeline_duration_ms.toFixed(1)}ms</span></div>
        `;

        // Render Candidates
        candidatesContainer.innerHTML = '';
        data.candidates.forEach(candidate => {
            const card = document.createElement('div');
            card.className = 'candidate-card';
            
            // Generate Links HTML
            let linksHtml = '';
            if (candidate.emails && candidate.emails.length > 0) {
                // Only render the first email as the primary contact button to avoid UI clutter
                const primaryEmail = candidate.emails[0];
                const href = primaryEmail.startsWith("mailto:") ? primaryEmail : `mailto:${primaryEmail}`;
                linksHtml += `<a href="${href}"><i class="fa-solid fa-envelope"></i> Email</a>`;
            }
            if (candidate.links) {
                if (candidate.links.linkedin) linksHtml += `<a href="${candidate.links.linkedin}" target="_blank"><i class="fa-brands fa-linkedin"></i> LinkedIn</a>`;
                if (candidate.links.github) linksHtml += `<a href="${candidate.links.github}" target="_blank"><i class="fa-brands fa-github"></i> GitHub</a>`;
                if (candidate.links.portfolio) linksHtml += `<a href="${candidate.links.portfolio}" target="_blank"><i class="fa-solid fa-globe"></i> Portfolio</a>`;
            }

            // Generate Interactive View HTML (Skills, Experience, Projects, Education)
            let interactiveHtml = '';
            
            if (candidate.skills && candidate.skills.length > 0) {
                interactiveHtml += `
                    <h4 class="section-title"><i class="fa-solid fa-code"></i> Skills</h4>
                    <div class="skills-grid">
                        ${candidate.skills.map(s => `<div class="skill-tag">${s.name} <span class="conf">${Math.round(s.confidence * 100)}%</span></div>`).join('')}
                    </div>
                `;
            }

            if (candidate.experience && candidate.experience.length > 0) {
                interactiveHtml += `
                    <h4 class="section-title"><i class="fa-solid fa-briefcase"></i> Experience</h4>
                    <div class="timeline">
                        ${candidate.experience.map(exp => `
                            <div class="timeline-item">
                                <h4>${exp.title || 'Unknown Role'} <span class="company">${exp.company ? '@ ' + exp.company : ''}</span></h4>
                                <div class="dates">${exp.start || ''} - ${exp.end || 'Present'}</div>
                                <div class="summary">${(exp.summary || '').replace(/\n/g, '<br>')}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            if (candidate.projects && candidate.projects.length > 0) {
                interactiveHtml += `
                    <h4 class="section-title"><i class="fa-solid fa-laptop-code"></i> Projects</h4>
                    <div class="timeline">
                        ${candidate.projects.map(proj => `
                            <div class="timeline-item">
                                <h4>${proj.title || 'Unknown Project'} <span class="company">${proj.company ? '@ ' + proj.company : ''}</span></h4>
                                <div class="dates">${proj.start || ''} ${proj.end ? '- ' + proj.end : ''}</div>
                                <div class="summary">${(proj.summary || '').replace(/\n/g, '<br>')}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            if (candidate.education && candidate.education.length > 0) {
                interactiveHtml += `
                    <h4 class="section-title"><i class="fa-solid fa-graduation-cap"></i> Education</h4>
                    <div class="timeline">
                        ${candidate.education.map(edu => `
                            <div class="timeline-item">
                                <h4>${edu.institution || 'Unknown Institution'}</h4>
                                <div class="dates">Graduated: ${edu.end_year || 'N/A'}</div>
                                <div class="summary">${edu.degree || ''} ${edu.field || ''}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            // Generate Canonical JSON Output for Textual View
            const jsonString = JSON.stringify(candidate, null, 2);
            const escapedJson = jsonString.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            
            // Simple regex for JSON syntax highlighting
            const highlightedJson = escapedJson.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                let color = '#38bdf8'; // number (blue)
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        color = '#f472b6'; // key (pink)
                    } else {
                        color = '#a3e635'; // string (green)
                    }
                } else if (/true|false/.test(match)) {
                    color = '#fb923c'; // boolean (orange)
                } else if (/null/.test(match)) {
                    color = '#94a3b8'; // null (gray)
                }
                return '<span style="color: ' + color + ';">' + match + '</span>';
            });

            const b64Json = btoa(unescape(encodeURIComponent(jsonString)));

            const jsonHtml = `
                <div class="json-output-container" style="margin-top: 1rem; background: rgba(15, 23, 42, 0.6); padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: inset 0 2px 10px rgba(0,0,0,0.2);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.5rem;">
                        <h4 style="margin: 0; color: #cbd5e1; font-family: 'Inter', sans-serif; font-size: 1rem;">
                            <i class="fa-solid fa-code" style="color: #38bdf8; margin-right: 8px;"></i> Canonical JSON Profile
                        </h4>
                        <div style="display: flex; gap: 10px;">
                            <button onclick="navigator.clipboard.writeText(decodeURIComponent(escape(atob('${b64Json}')))); this.innerHTML='<i class=\\'fa-solid fa-check\\'></i> Copied!'; setTimeout(()=>this.innerHTML='<i class=\\'fa-regular fa-copy\\'></i> Copy', 2000);" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 5px; transition: all 0.2s;">
                                <i class="fa-regular fa-copy"></i> Copy
                            </button>
                            <a href="data:application/json;charset=utf-8;base64,${b64Json}" download="${candidate.candidate_id || 'profile'}.json" style="background: var(--primary-color); border: none; color: white; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 0.8rem; text-decoration: none; display: inline-flex; align-items: center; gap: 5px; transition: all 0.2s;">
                                <i class="fa-solid fa-download"></i> Download
                            </a>
                        </div>
                    </div>
                    <pre style="margin: 0; overflow-x: auto;"><code style="font-family: 'Consolas', 'Monaco', monospace; font-size: 0.85rem; line-height: 1.5;">${highlightedJson}</code></pre>
                </div>
            `;

            const overallScore = Math.round((candidate.overall_confidence || 0) * 100);

            card.innerHTML = `
                <div class="profile-header">
                    <div class="profile-info">
                        <h3>${candidate.full_name || 'Unknown Candidate'}</h3>
                        <div class="profile-meta">
                            ${candidate.location && candidate.location.city ? `<div><i class="fa-solid fa-location-dot"></i> ${candidate.location.city}, ${candidate.location.country || ''}</div>` : ''}
                            ${candidate.years_experience ? `<div><i class="fa-solid fa-calendar-check"></i> ${candidate.years_experience} YOE</div>` : ''}
                        </div>
                        <div class="links-container">
                            ${linksHtml}
                        </div>
                    </div>
                    <div class="confidence-score">
                        <div class="score-circle" style="--score: ${overallScore}">
                            <span>${overallScore}%</span>
                        </div>
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;">Confidence</div>
                    </div>
                </div>
                <div class="card-view-interactive">
                    ${interactiveHtml}
                </div>
                <div class="card-view-textual hidden">
                    ${jsonHtml}
                </div>
            `;
            
            candidatesContainer.appendChild(card);
        });
        
        resultsSection.classList.remove('hidden');
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    // Handle View Mode Toggle
    const toggleInteractive = document.getElementById('toggle-interactive');
    const toggleTextual = document.getElementById('toggle-textual');

    if (toggleInteractive && toggleTextual) {
        toggleInteractive.addEventListener('click', () => {
            toggleInteractive.style.background = 'var(--primary-color)';
            toggleTextual.style.background = 'transparent';
            
            document.querySelectorAll('.card-view-interactive').forEach(el => el.classList.remove('hidden'));
            document.querySelectorAll('.card-view-textual').forEach(el => el.classList.add('hidden'));
        });

        toggleTextual.addEventListener('click', () => {
            toggleTextual.style.background = 'var(--primary-color)';
            toggleInteractive.style.background = 'transparent';
            
            document.querySelectorAll('.card-view-textual').forEach(el => el.classList.remove('hidden'));
            document.querySelectorAll('.card-view-interactive').forEach(el => el.classList.add('hidden'));
        });
    }
});
