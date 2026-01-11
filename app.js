document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('clip-grid');
    const modalOverlay = document.getElementById('modal-overlay');
    const modalClose = document.getElementById('modal-close');
    const modalVideo = document.getElementById('modal-video');
    const totalClipsEl = document.getElementById('total-clips');
    const totalDurationEl = document.getElementById('total-duration');

    let allClips = [];

    // Define Threads
    const THREADS = {
        'Becker Contagion': {
            pattern: /Becker Contagion/i,
            desc: "Systemic Misidentification: This thread highlights the catastrophic failure to properly identify the 'Most Wanted' fugitive Christopher Foster. By accepting the false alias 'Ed Becker', law enforcement allowed a dangerous criminal to be released while prosecuting the disabled victim."
        },
        'Coordinated Extraction': {
            pattern: /Coordinated Extraction/i,
            desc: "The Passenger Conspiracy: Evidence suggests a premeditated plan by the passengers to use Mr. Vega as a shield. This includes the unexplained flight of Danielle Allen and the potential coordination with third parties (e.g., the off-duty officer theory)."
        },
        'Calculated Disablement': {
            pattern: /Calculated Disablement/i,
            desc: "Physical Duress & Encirclement: By violently ejecting Mr. Vega's walker from the vehicle, the co-conspirators stripped him of his only means of independent mobility. This act physically trapped him in the driver's seat, cementing the duress."
        },
        'Scapegoat Gambit': {
            pattern: /Scapegoat Gambit/i,
            desc: "Framing the Vulnerable: This validates Mr. Vega's claim of innocent intent (e.g., the Hobby Town trip) and exposes the State's arbitrary charging decisions. It contrasts his genuine confusion with the calculated deception of his passengers."
        },
        'Unconscionable Price': {
            pattern: /Unconscionable Price/i,
            desc: "Medical Incompatibility: Demonstrating that Mr. Vega's unique physical condition (triple amputee with a failing prototype implant) renders standard incarceration not just difficult, but constitutionally excessive and dangerous."
        },
        'Percival Echo': {
            pattern: /Percival Echo/i,
            desc: "Consequences of Release: Documenting the direct causal link between the 'Becker' misidentification and the subsequent tragic death of Stacy Percival. It underscores the high stakes of the initial police failure."
        },
        'Illusion of Choice': {
            pattern: /Illusion of Choice/i,
            desc: "Psychological & Physical Duress: Evidence that Mr. Vega was operating under extreme fear ('Freeze/Appease' response) and contradictory commands, negating the 'willful' element required for the fleeing charge."
        },
        'Police Conduct': {
            pattern: /Unprofessionalism|Misconduct|Corruption|Giglio/i,
            desc: "Investigative Failures: Instances of potential bias, mishandling of evidence (e.g., theft jokes), and procedural violations that undermine the integrity of the prosecution's case."
        }
    };

    // Load Data
    const runSelector = document.getElementById('run-selector');

    if (typeof MULTI_RUN_DATA !== 'undefined' && Object.keys(MULTI_RUN_DATA).length > 0) {
        // Sort so "Latest Processed" is first, then valid runs by date desc
        const runs = Object.keys(MULTI_RUN_DATA).sort((a, b) => {
            if (a.includes("Latest")) return -1;
            if (b.includes("Latest")) return 1;
            return b.localeCompare(a); // Descending date
        });

        runs.forEach(runId => {
            const opt = document.createElement('option');
            opt.value = runId;
            opt.textContent = runId;
            runSelector.appendChild(opt);
        });

        const loadRun = (runId) => {
            if (MULTI_RUN_DATA[runId]) {
                allClips = MULTI_RUN_DATA[runId];
                initDashboard();
            }
        };

        // Default to first (latest)
        if (runs.length > 0) loadRun(runs[0]);

        runSelector.addEventListener('change', (e) => {
            loadRun(e.target.value);
        });

    } else {
        // Fallback
        if (runSelector) runSelector.style.display = 'none';

        if (typeof CLIPS_DATA !== 'undefined') {
            allClips = CLIPS_DATA;
            initDashboard();
        } else {
            console.error('CLIPS_DATA not found. attempting fetch...');
            fetch('clips/clips_metadata.json')
                .then(response => response.json())
                .then(data => {
                    allClips = data;
                    initDashboard();
                })
                .catch(err => {
                    console.error('Error loading clips:', err);
                    grid.innerHTML = '<div style="color: #f85149; padding: 2rem;">Error loading data. If opening locally, ensure data.js is loaded.</div>';
                });
        }
    }

    function initDashboard() {
        updateStats();
        renderGroupedClips();
    }

    function updateStats() {
        totalClipsEl.textContent = allClips.length;
        const totalSeconds = allClips.reduce((acc, clip) => acc + (clip.duration_seconds || 0), 0);
        const minutes = Math.floor(totalSeconds / 60);
        totalDurationEl.textContent = `${minutes}m`;
    }

    function identifyThreads(clip) {
        const text = (clip.significance + " " + clip.description).toLowerCase();
        const found = [];

        for (const [key, config] of Object.entries(THREADS)) {
            if (config.pattern.test(text)) {
                found.push(key);
            }
        }

        return found.length > 0 ? found : ['General Evidence'];
    }

    function renderGroupedClips() {
        grid.innerHTML = '';

        // Group clips
        const groups = {};
        Object.keys(THREADS).forEach(k => groups[k] = []);
        groups['General Evidence'] = [];

        allClips.forEach(clip => {
            const clipThreads = identifyThreads(clip);
            const primaryThread = clipThreads[0];
            if (!groups[primaryThread]) groups[primaryThread] = [];
            groups[primaryThread].push(clip);
        });

        // Loop and render
        const threadKeys = Object.keys(THREADS);
        let index = 0;

        for (const [category, clips] of Object.entries(groups)) {
            if (clips.length === 0) continue;
            clips.sort((a, b) => a.id.localeCompare(b.id));

            // Section Container
            const section = document.createElement('section');
            section.className = 'thread-section';

            // Calculate Hue (Start at ~200 for Blues/Teals and rotate)
            // 200 = Blue-Cyan. 
            // Spread across 8-9 items. ~40 degree shift.
            const hue = (200 + (index * 40)) % 360;
            section.style.background = `hsla(${hue}, 60%, 15%, 0.4)`;
            // Add a subtle border of the same hue but brighter
            section.style.borderColor = `hsla(${hue}, 60%, 30%, 0.3)`;

            // Header
            const header = document.createElement('div');
            header.className = 'group-header';
            header.innerHTML = `
                <div class="group-title">
                    ${category}: <span style="font-weight: 400; font-size: 0.9em; text-transform: none; color: rgba(255,255,255,0.7); margin-left: 0.5rem;">${THREADS[category] ? THREADS[category].desc : ''}</span>
                    <span class="group-count">${clips.length}</span>
                </div>
            `;
            section.appendChild(header);

            // Grid using .thread-grid class now
            const threadGrid = document.createElement('div');
            threadGrid.className = 'thread-grid';

            clips.forEach(clip => {
                const card = createCard(clip);
                threadGrid.appendChild(card);
            });
            section.appendChild(threadGrid);

            grid.appendChild(section);
            index++;
        }
    }

    function createCard(clip) {
        const el = document.createElement('div');
        el.className = 'clip-card';

        // Robust path handling
        let videoSrc = "";
        if (clip.filename && clip.filename !== "") {
            videoSrc = `clips/${clip.filename}`;
        }

        el.innerHTML = `
            <div class="card-thumbnail">
                <video preload="metadata" muted onmouseover="this.play()" onmouseout="this.pause();this.currentTime=0;">
                    <source src="${videoSrc}" type="video/mp4">
                </video>
                <div class="play-icon">
                    <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                </div>
            </div>
            <div class="card-content">
                <div class="card-meta">
                    <span class="card-id">${clip.id.toUpperCase().split('_').pop().replace('.MP4', '')}</span>
                    <span>${formatTime(clip.duration_seconds)}</span>
                </div>
                <div class="card-title">${clip.description || 'No Description'}</div>
                <div class="card-tags">
                   <!-- <span class="tag">EVIDENCE</span> -->
                </div>
            </div>
        `;

        el.addEventListener('click', () => openModal(clip));
        return el;
    }

    function openModal(clip) {
        let videoSrc = "";
        if (clip.filename && clip.filename !== "") {
            videoSrc = `clips/${clip.filename}`;
        } else if (clip.original_video) {
            videoSrc = `../video/${clip.original_video}`;
        }

        document.getElementById('modal-title').textContent = clip.description;
        document.getElementById('modal-transcript').textContent = clip.transcript || "No transcript available.";
        document.getElementById('modal-significance').textContent = clip.significance || "No significance noted.";
        document.getElementById('modal-id').textContent = clip.id.toUpperCase();
        document.getElementById('modal-source').textContent = clip.original_video;
        document.getElementById('modal-timestamp').textContent = `${clip.start_time} - ${clip.end_time}`;

        modalVideo.src = videoSrc;
        modalVideo.play();

        modalOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeModal() {
        modalOverlay.classList.remove('active');
        modalVideo.pause();
        modalVideo.src = "";
        document.body.style.overflow = '';
    }

    modalClose.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    function formatTime(seconds) {
        if (!seconds) return "0s";
        return `${Math.round(seconds)}s`;
    }
});
