(function () {
    const cfg = window.REGISTRATION_CONFIG || {};
    const programsByLevel = cfg.programsByLevel || {};
    const levelSelect = document.getElementById('program_level');
    const nameSelect = document.getElementById('program_name');

    if (!levelSelect || !nameSelect) return;

    function populateProgramNames(level, selectedName) {
        const programs = level ? (programsByLevel[level] || []) : [];
        nameSelect.innerHTML = '<option value="">-- Select Program Name --</option>';

        programs.forEach(function (name) {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            nameSelect.appendChild(opt);
        });

        nameSelect.disabled = !level;

        if (selectedName && programs.includes(selectedName)) {
            nameSelect.value = selectedName;
        } else {
            nameSelect.value = '';
        }
    }

    levelSelect.addEventListener('change', function () {
        populateProgramNames(levelSelect.value, '');
    });

    populateProgramNames(
        cfg.initialProgramLevel || levelSelect.value,
        cfg.initialProgramName || ''
    );
})();