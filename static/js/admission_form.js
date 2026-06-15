/* Admission form wizard - ported from ASP.NET FillAdmissionForm.aspx */
(function () {
    let current = 0;
    let photoBase64 = '';
    let signBase64 = '';
    let isRestoringData = false;
    let saveTimer;
    let educationSaveTimer;
    const cfg = window.ADMISSION_CONFIG || {};
    let indiaStatesDistricts = {};
    let boardsUniversitiesData = {
        school_boards: [],
        chhattisgarh_universities: [],
        universities: [],
    };
    let bscSubjectGroups = [];
    let selectedBscGroup = '';
    const bscProgramName = cfg.bscProgramName || 'B.Sc.';
    const bscProgramNames = new Set([
        bscProgramName,
        ...(Array.isArray(cfg.bscProgramNames) ? cfg.bscProgramNames : []),
    ]);

    function initBscSubjectGroups() {
        const groupEl = document.getElementById('bsc-subject-groups-data');
        if (groupEl?.textContent) {
            try {
                bscSubjectGroups = JSON.parse(groupEl.textContent);
            } catch (e) {
                console.error('Failed to parse B.Sc. subject groups', e);
            }
        }
    }

    function isBscProgram(programType) {
        const name = (programType || '').trim();
        if (!name) return false;
        if (bscProgramNames.has(name)) return true;
        return /^b\.sc/i.test(name);
    }

    function isPgDcaProgram(programType) {
        const name = (programType || '').trim();
        if (!name) return false;
        const upper = name.toUpperCase();
        return upper.includes('P. G. D. C. A') || upper.includes('PGDCA') || /P\.?\s*G\.?\s*D\.?\s*C\.?\s*A/i.test(name);
    }

    const programsByLevel = cfg.programsByLevel || {};

    function isEducationRowVisible(rowId) {
        const row = document.getElementById(rowId);
        return !!(row && row.style.display !== 'none');
    }

    function getRowStream(rowId) {
        const row = document.getElementById(rowId);
        if (!row || row.style.display === 'none') return '';
        return (row.querySelector('.stream')?.value || '').trim();
    }

    function getEducationEligibility() {
        const has12th = true;
        const hasGrad = isEducationRowVisible('rowGrad');
        const stream12 = getRowStream('row12th');
        const streamGrad = hasGrad ? getRowStream('rowGrad') : '';
        const canSelectUG = !!stream12;
        const canSelectPG = !!stream12 && hasGrad && !!streamGrad;
        const canSelectDiploma = !!stream12;
        const canShowPgDca = canSelectPG;
        return {
            has12th,
            hasGrad,
            stream12,
            streamGrad,
            canSelectUG,
            canSelectPG,
            canSelectDiploma,
            canShowPgDca,
            showBsc: canSelectUG && stream12 === 'Science',
        };
    }

    function levelEligibilityMap() {
        const elig = getEducationEligibility();
        return {
            UG: elig.canSelectUG,
            PG: elig.canSelectPG,
            Diploma: elig.canSelectDiploma,
        };
    }

    function getFilteredProgramsForLevel(level) {
        const programs = level ? (programsByLevel[level] || []) : [];
        const elig = getEducationEligibility();
        if (level === 'UG') {
            if (!elig.showBsc) return programs.filter(name => !isBscProgram(name));
        }
        if (level === 'Diploma' && !elig.canShowPgDca) {
            return programs.filter(name => !isPgDcaProgram(name));
        }
        return programs;
    }

    function clearCourseTable(message) {
        const tbody = document.getElementById('courseTableBody');
        if (tbody) tbody.innerHTML = `<tr><td colspan="4">${message || 'Select a program name'}</td></tr>`;
        updateBscGroupSectionVisibility('');
        const bscSection = document.getElementById('bscGroupSection');
        if (bscSection) bscSection.hidden = true;
        selectedBscGroup = '';
        updateSelectedGroupBadge();
    }

    function refreshProgramLevelDropdown() {
        const ddl = document.getElementById('ddlProgramLevel');
        if (!ddl) return;
        const rules = levelEligibilityMap();
        Array.from(ddl.options).forEach(opt => {
            if (!opt.value) return;
            opt.disabled = !rules[opt.value];
        });
    }

    function updateCourseStepHint() {
        const hint = document.getElementById('courseEligibilityHint');
        if (!hint) return;
        const elig = getEducationEligibility();
        hint.hidden = elig.canSelectUG;
    }

    function refreshProgramOptionsFromEducation() {
        refreshProgramLevelDropdown();
        updateCourseStepHint();
        const levelDdl = document.getElementById('ddlProgramLevel');
        const nameDdl = document.getElementById('ddlProgramType');
        if (!levelDdl || !nameDdl) return;
        const rules = levelEligibilityMap();
        const currentLevel = levelDdl.value;
        const currentName = nameDdl.value;
        if (currentLevel && !rules[currentLevel]) {
            levelDdl.value = '';
            populateProgramNames('');
            clearCourseTable('Complete Education step to see programs');
            return;
        }
        if (!currentLevel) {
            populateProgramNames('');
            if (!rules.UG && !rules.PG && !rules.Diploma) {
                clearCourseTable('Complete Education step to see programs');
            }
            return;
        }
        const filtered = getFilteredProgramsForLevel(currentLevel);
        const chosen = populateProgramNames(currentLevel, currentName);
        if (currentName && !filtered.includes(currentName) && !chosen) {
            clearCourseTable('Selected program is not available for your education stream');
        } else if (chosen && chosen !== currentName) {
            loadCourses(chosen);
        } else if (chosen && isBscProgram(chosen) && !getEducationEligibility().showBsc) {
            levelDdl.value = '';
            populateProgramNames('');
            clearCourseTable('B.Sc. programs require 12th Science stream');
        } else if (chosen && isPgDcaProgram(chosen) && !getEducationEligibility().canShowPgDca) {
            levelDdl.value = '';
            populateProgramNames('');
            clearCourseTable('P.G.D.C.A. requires 12th and Graduation with stream');
        }
    }

    function allProgramNames() {
        const names = [];
        Object.values(programsByLevel).forEach(list => {
            (list || []).forEach(name => names.push(name));
        });
        return names;
    }

    function getProgramDropdownOptions() {
        const ddl = document.getElementById('ddlProgramType');
        if (!ddl) return [];
        return Array.from(ddl.options).map(o => o.value).filter(Boolean);
    }

    function inferProgramLevel(programName) {
        const name = (programName || '').trim();
        if (!name) return '';
        for (const [level, names] of Object.entries(programsByLevel)) {
            if ((names || []).includes(name)) return level;
        }
        if (isBscProgram(name)) {
            for (const [level, names] of Object.entries(programsByLevel)) {
                const match = (names || []).find(item => isBscProgram(item));
                if (match) return level;
            }
        }
        return '';
    }

    function setProgramLevelDropdown(level) {
        const ddl = document.getElementById('ddlProgramLevel');
        if (ddl && level) ddl.value = level;
    }

    function populateProgramNames(level, selectedName) {
        const ddl = document.getElementById('ddlProgramType');
        if (!ddl) return '';
        const programs = level ? getFilteredProgramsForLevel(level) : [];
        ddl.innerHTML = '<option value="">-- Select Program Name --</option>';
        programs.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            ddl.appendChild(opt);
        });
        let chosen = '';
        if (selectedName) {
            chosen = normalizeProgramTypeForDropdown(selectedName, programs);
            if (chosen && !programs.includes(chosen)) {
                const opt = document.createElement('option');
                opt.value = chosen;
                opt.textContent = chosen;
                ddl.appendChild(opt);
            }
            if (chosen) ddl.value = chosen;
        }
        return chosen;
    }

    function initProgramDropdowns(programLevel, programName) {
        const level = programLevel || inferProgramLevel(programName) || cfg.initialProgramLevel || '';
        if (level) setProgramLevelDropdown(level);
        const chosen = populateProgramNames(level, programName || cfg.initialProgramType || '');
        return { level, programName: chosen };
    }

    function normalizeProgramTypeForDropdown(programType, programList) {
        const requested = (programType || cfg.initialProgramType || '').trim();
        if (!requested) return val('ddlProgramType');
        const options = programList || getProgramDropdownOptions();
        const fallbackOptions = options.length ? options : allProgramNames();
        if (fallbackOptions.includes(requested)) return requested;
        if (isBscProgram(requested)) {
            const match = fallbackOptions.find(o => isBscProgram(o));
            if (match) return match;
        }
        return requested;
    }

    function setProgramDropdown(programType) {
        const level = inferProgramLevel(programType) || val('ddlProgramLevel') || cfg.initialProgramLevel;
        if (level) setProgramLevelDropdown(level);
        return populateProgramNames(level, programType);
    }

    function getBscGroupFullName(groupKey) {
        const group = findBscGroup(groupKey);
        if (!group) return '';
        return group.full_name || `${group.heading} — ${group.label}`;
    }

    function updateBscGroupSectionVisibility(programType) {
        const section = document.getElementById('bscGroupSection');
        const groupCol = document.getElementById('courseGroupCol');
        if (section) section.hidden = !isBscProgram(programType);
        if (groupCol) groupCol.hidden = !isBscProgram(programType);
    }

    function updateSelectedGroupBadge() {
        const badge = document.getElementById('bscSelectedGroupName');
        if (!badge) return;
        if (!selectedBscGroup) {
            badge.hidden = true;
            badge.textContent = '';
            return;
        }
        const fullName = getBscGroupFullName(selectedBscGroup);
        badge.hidden = !fullName;
        badge.textContent = fullName ? `Selected Group: ${fullName}` : '';
    }

    function val(id) {
        const el = document.getElementById(id);
        return el ? el.value.trim() : '';
    }

    function getAppNo() {
        const el = document.getElementById('lblAppNo');
        if (!el) return cfg.draftAppNo || '';
        const text = (el.textContent || el.innerText || '').trim();
        if (!text || text === 'Not Generated') return cfg.draftAppNo || '';
        return text;
    }

    function syncUploadBase64() {
        const photoImg = document.getElementById('imgPhotoPreview');
        const signImg = document.getElementById('imgSignPreview');
        if (!photoBase64 && photoImg?.src?.startsWith('data:image')) photoBase64 = photoImg.src;
        if (!signBase64 && signImg?.src?.startsWith('data:image')) signBase64 = signImg.src;
    }

    function updatePreviewButtonVisibility() {
        const previewBtn = document.getElementById('btnPreview');
        const chk = document.getElementById('declarationCheck');
        if (!previewBtn) return;
        const onLastStep = current === getSteps().length - 1;
        previewBtn.style.display = (onLastStep && chk?.checked) ? 'inline-flex' : 'none';
    }

    function getSteps() {
        return document.querySelectorAll('.form-step');
    }

    function getTabs() {
        return document.querySelectorAll('.tab-btn');
    }

    function showStep(i) {
        const steps = getSteps();
        const tabs = getTabs();
        if (i < 0 || i >= steps.length) return;
        current = i;
        steps.forEach((s, idx) => {
            s.classList.toggle('active', idx === i);
            s.setAttribute('aria-hidden', idx !== i);
        });
        tabs.forEach((t, idx) => t.classList.toggle('active', idx === i));
        const prevBtn = document.getElementById('btnPrev');
        const nextBtn = document.getElementById('btnNext');
        const previewBtn = document.getElementById('btnPreview');
        if (prevBtn) prevBtn.style.display = i === 0 ? 'none' : 'inline-flex';
        if (nextBtn) nextBtn.style.display = i === steps.length - 1 ? 'none' : 'inline-flex';
        updatePreviewButtonVisibility();
        document.getElementById('hdnActiveStep').value = i;
        if (i === 3) {
            refreshProgramOptionsFromEducation();
        }
    }

    function advanceStep(dir) {
        if (current + dir >= 0 && current + dir < getSteps().length) {
            showStep(current + dir);
            updateTabStatus();
        }
    }

    window.changeStep = function (dir) {
        const steps = getSteps();
        if (dir > 0 && !isStepValid(steps[current])) return false;
        if (cfg.formDisabled) {
            advanceStep(dir);
            return false;
        }
        const nextBtn = document.getElementById('btnNext');
        const prevLabel = nextBtn ? nextBtn.textContent : '';
        if (nextBtn && dir > 0) {
            nextBtn.disabled = true;
            nextBtn.textContent = 'Saving...';
        }
        const nextStep = current + dir;
        const saveOptions = { activeStep: dir > 0 ? nextStep : current };
        if (current === 2 && dir > 0) {
            saveOptions.education = collectEducationRows();
        }
        saveDraftNow(saveOptions)
            .then(res => {
                if (res && res.status !== 'DRAFT_SAVED') {
                    console.warn('Draft save returned unexpected status', res);
                }
                advanceStep(dir);
            })
            .catch(err => {
                console.error('Draft save failed on step change', err);
                alert('Could not save your progress. Please check your connection and try again.');
            })
            .finally(() => {
                if (nextBtn) {
                    nextBtn.disabled = false;
                    nextBtn.textContent = prevLabel || 'Next';
                }
            });
        return false;
    };

    window.jumpToStep = function (i) {
        if (cfg.formDisabled) {
            showStep(i);
            updateTabStatus();
            return false;
        }
        const go = () => {
            if (i <= current || canJumpTo(i)) {
                showStep(i);
                updateTabStatus();
            } else {
                alert('Please complete previous steps first.');
            }
        };
        saveDraftNow().catch(err => console.error('Draft save failed on tab jump', err)).finally(go);
        return false;
    };

    function isStepValid(step) {
        if (!step || cfg.formDisabled) return true;
        const stepIdx = parseInt(step.getAttribute('data-step'));
        if (stepIdx === 4) {
            if (!photoBase64) { alert('Please upload passport photo.'); return false; }
            if (!signBase64) { alert('Please upload signature.'); return false; }
            return true;
        }
        if (stepIdx === 5) return true;
        const fields = step.querySelectorAll('input[required], select[required], textarea[required]');
        for (const f of fields) {
            if (f.offsetWidth === 0 && f.offsetHeight === 0) continue;
            if (!f.value.trim()) {
                f.classList.add('required-error');
                f.scrollIntoView({ behavior: 'smooth', block: 'center' });
                alert('Please fill all required fields in this step.');
                return false;
            }
            f.classList.remove('required-error');
        }
        if (stepIdx === 2) {
            const elig = getEducationEligibility();
            if (!elig.stream12) {
                alert('Please select stream for 12th (Science / Arts / Commerce).');
                document.getElementById('ddlStream12')?.focus();
                return false;
            }
            if (elig.hasGrad && !elig.streamGrad) {
                alert('Please select stream for Graduation.');
                document.getElementById('ddlStreamGrad')?.focus();
                return false;
            }
        }
        if (stepIdx === 3) {
            const elig = getEducationEligibility();
            if (!elig.canSelectUG) {
                alert('Please complete 12th education with stream before selecting a course.');
                return false;
            }
            if (!val('ddlProgramLevel')) {
                alert('Please select a program type (First Under Graduate / Post Graduate / Diploma).');
                return false;
            }
            const rules = levelEligibilityMap();
            const selectedLevel = val('ddlProgramLevel');
            if (selectedLevel && !rules[selectedLevel]) {
                alert('This program type is not available for your education details.');
                return false;
            }
            if (!val('ddlProgramType')) {
                alert('Please select a program name.');
                return false;
            }
            if (isBscProgram(val('ddlProgramType'))) {
                if (!selectedBscGroup) {
                    alert('Please select one B.Sc. subject group (Bio or Maths).');
                    return false;
                }
                const group = findBscGroup(selectedBscGroup);
                const groupCourses = Array.from(document.querySelectorAll('#courseTableBody tr'))
                    .filter(tr => !tr.hidden
                        && tr.dataset.groupCourse === '1'
                        && rowInSelectedGroup(tr, group, selectedBscGroup));
                const missingGroupCourse = groupCourses.some(tr => {
                    const chk = tr.querySelector('input[type=checkbox]');
                    if (!chk) return true;
                    const mustSelect = isDscRow(tr) || tr.dataset.dbCompulsory === '1';
                    return mustSelect && !chk.checked;
                });
                if (missingGroupCourse) {
                    alert('Please wait for group subjects to load, or re-select your B.Sc. group.');
                    return false;
                }
            }
            const checked = document.querySelectorAll('#courseTableBody input[type=checkbox]:checked');
            if (!checked.length) { alert('Please select at least one course.'); return false; }
        }
        return true;
    }

    function isStepFilled(step) {
        if (!step) return false;
        const idx = parseInt(step.getAttribute('data-step'));
        if (idx === 4) return !!photoBase64 && !!signBase64;
        if (idx === 5) return document.getElementById('declarationCheck')?.checked;
        if (idx === 2) {
            const elig = getEducationEligibility();
            if (!elig.stream12) return false;
            if (elig.hasGrad && !elig.streamGrad) return false;
        }
        const req = step.querySelectorAll('input[required], select[required]');
        for (const f of req) {
            if (f.offsetWidth === 0) continue;
            if (!f.value.trim()) return false;
        }
        return true;
    }

    function canJumpTo(target) {
        const steps = getSteps();
        for (let i = 0; i < target; i++) {
            if (!isStepFilled(steps[i])) return false;
        }
        return true;
    }

    function updateTabStatus() {
        const steps = getSteps();
        const tabs = getTabs();
        steps.forEach((s, i) => {
            if (tabs[i]) tabs[i].classList.toggle('done', isStepFilled(s));
        });
    }

    function getStorageKey() {
        return 'admission_draft_' + (cfg.regNo || 'guest');
    }

    function collectEducationRows() {
        const education = [];
        document.querySelectorAll('.edu-data-row').forEach(row => {
            if (row.id === 'rowGrad' && !isEducationRowVisible('rowGrad')) return;
            let classNameVal = (row.querySelector('.class-name')?.value || '').trim();
            if (!classNameVal) {
                if (row.id === 'row10th') classNameVal = '10th';
                else if (row.id === 'row12th') classNameVal = '12th';
                else return;
            }
            education.push({
                ClassName: classNameVal,
                Board: row.querySelector('.board')?.value || '',
                Stream: row.querySelector('.stream')?.value || '',
                Duration: row.querySelector('.duration')?.value || '',
                Year: row.querySelector('.year')?.value || '',
                TotalMarks: row.querySelector('.total-marks')?.value || '',
                Obtained: row.querySelector('.obtainedmarks')?.value || '',
                Percentage: row.querySelector('.percentage')?.value || '',
                Grade: row.querySelector('.grade')?.value || '',
            });
        });
        return education;
    }

    function collectFormData() {
        const education = collectEducationRows();
        const selectedSubjectsArr = [];
        document.querySelectorAll('#courseTableBody input[type=checkbox]:checked').forEach(chk => {
            const row = chk.closest('tr');
            if (row) {
                selectedSubjectsArr.push({
                    name: row.dataset.name || '',
                    type1: row.dataset.type1 || '',
                    type2: row.dataset.type2 || '',
                });
            }
        });
        selectedSubjectsArr.sort((a, b) => {
            const prio = s => {
                const t2 = (s.type2 || '').toUpperCase();
                const t1 = (s.type1 || '').toLowerCase();
                if (t2 === 'AEC') return 1;
                if (t2 === 'DSC') return (t1.includes('practical') || t1.includes('lab')) ? 3 : 2;
                if (t2 === 'GE') return (t1.includes('practical') || t1.includes('lab')) ? 5 : 4;
                if (t2 === 'SEC') return 6;
                return 99;
            };
            return prio(a) - prio(b);
        });

        const appNo = getAppNo();
        syncUploadBase64();
        return {
            ApplicationNo: appNo,
            ActiveStep: current,
            ProgramType: val('ddlProgramType'),
            ProgramLevel: val('ddlProgramLevel'),
            BScSubjectGroup: selectedBscGroup,
            CourseName: '',
            Subject: selectedSubjectsArr.map(s => s.name).join(', '),
            SelectedSubjects: selectedSubjectsArr,
            FullName: val('txtName'),
            FatherName: val('txtFather'),
            MotherName: val('txtMother'),
            Gender: val('ddlGender'),
            Category: val('ddlCategory'),
            Nationality: val('txtNationality') || 'Indian',
            Religion: val('ddlReligion'),
            MaritalStatus: val('ddlMaritalStatus'),
            BloodGroup: val('ddlBloodGroup'),
            DOB: val('txtDOB'),
            Mobile: val('txtMobile'),
            Email: val('txtEmail'),
            Aadhaar: val('txtAadhaar'),
            Apaar: val('txtApaar'),
            HasDisability: val('ddlDisabilityCertificate') === 'Yes' ? 1 : 0,
            DisabilityDetails: val('txtDisabilityDetails'),
            DisabilityPercentage: val('txtDisabilityPercentage'),
            DisabilityType: val('txtDisabilityType'),
            Minority: val('ddlMinority'),
            Medium: val('ddlMedium'),
            PermState: val('txtPerState'),
            PermDistrict: val('txtPerDistrict'),
            PermCity: val('txtPerCity'),
            PermVillage: val('txtPerVillage'),
            PermPinCode: val('txtPerPin'),
            CorrState: val('txtCorState'),
            CorrDistrict: val('txtCorDistrict'),
            CorrCity: val('txtCorCity'),
            CorrVillage: val('txtCorVillage'),
            CorrPinCode: val('txtCorPin'),
            PhotoBase64: photoBase64,
            SignatureBase64: signBase64,
            Education: education,
            DeclarationAccepted: !!document.getElementById('declarationCheck')?.checked,
            WizardVersion: 2,
        };
    }

    function persistDraftLocally(data) {
        try {
            localStorage.setItem(getStorageKey(), JSON.stringify(data));
        } catch (e) {
            console.error('Failed to persist draft locally', e);
        }
    }

    function getEmbeddedDraft() {
        const draftEl = document.getElementById('draft-data');
        if (!draftEl?.textContent) return null;
        try {
            const parsed = JSON.parse(draftEl.textContent);
            if (parsed && typeof parsed === 'object' && Object.keys(parsed).length) {
                return parsed;
            }
        } catch (e) {
            console.error('Failed to parse embedded draft data', e);
        }
        return null;
    }

    function pickBestEducation(...sources) {
        for (const src of sources) {
            if (!src) continue;
            const edu = getDraftEducation(src);
            if (educationHasContent(edu)) return edu;
        }
        for (const src of sources) {
            if (!src) continue;
            const edu = getDraftEducation(src);
            if (edu.length) return edu;
        }
        return [];
    }

    function persistEducationDraftLocally() {
        if (isRestoringData || cfg.formDisabled) return;
        const data = collectFormData();
        persistDraftLocally(data);
        refreshProgramOptionsFromEducation();
        clearTimeout(educationSaveTimer);
        educationSaveTimer = setTimeout(() => {
            saveDraftNow({ education: collectEducationRows() }).catch(err => {
                console.error('Education auto-save failed', err);
            });
        }, 350);
    }

    function bindEducationPersistence() {
        if (cfg.formDisabled) return;
        const selector = '#row10th input, #row10th select, #row12th input, #row12th select, #rowGrad input, #rowGrad select';
        document.querySelectorAll(selector).forEach(el => {
            el.addEventListener('input', persistEducationDraftLocally);
            el.addEventListener('change', persistEducationDraftLocally);
        });
    }

    function snapshotDraftToLocal() {
        if (isRestoringData || cfg.formDisabled) return;
        persistDraftLocally(collectFormData());
    }

    function applySavedAppNo(appNo, data) {
        if (!appNo) return;
        const lbl = document.getElementById('lblAppNo');
        if (lbl) lbl.textContent = appNo;
        cfg.draftAppNo = appNo;
        if (data) {
            data.ApplicationNo = appNo;
            persistDraftLocally(data);
        }
    }

    function saveDraftNow(options = {}) {
        if (isRestoringData || cfg.formDisabled) return Promise.resolve(null);
        clearTimeout(saveTimer);
        const data = collectFormData();
        if (typeof options.activeStep === 'number') {
            data.ActiveStep = options.activeStep;
        }
        if (Array.isArray(options.education) && options.education.length) {
            data.Education = options.education;
        }
        persistDraftLocally(data);
        return fetch(cfg.saveDraftUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.csrfToken },
            body: JSON.stringify(data),
        })
            .then(r => r.json().then(res => ({ ok: r.ok, res })))
            .then(({ ok, res }) => {
                if (!ok || res.status !== 'DRAFT_SAVED') {
                    throw new Error(res?.message || 'Draft save failed');
                }
                if (res.application_no) applySavedAppNo(res.application_no, data);
                return res;
            })
            .catch(err => {
                console.error('Draft save failed', err);
                throw err;
            });
    }

    function unifiedAutoSave() {
        if (isRestoringData || cfg.formDisabled) return;
        clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
            saveDraftNow().catch(err => console.error('Auto-save failed', err));
        }, 600);
    }

    window.previewFile = function (e, type) {
        const file = e.target.files[0];
        if (!file) return;
        const allowed = ['image/jpeg', 'image/jpg', 'image/png'];
        const maxSize = type === 'photo' ? 100 * 1024 : 50 * 1024;
        if (!allowed.includes(file.type)) { alert('Only JPG/PNG allowed.'); e.target.value = ''; return; }
        if (file.size > maxSize) { alert(type === 'photo' ? 'Photo max 100KB' : 'Signature max 50KB'); e.target.value = ''; return; }
        const reader = new FileReader();
        reader.onload = ev => {
            const base64 = ev.target.result;
            const imgId = type === 'photo' ? 'imgPhotoPreview' : 'imgSignPreview';
            const img = document.getElementById(imgId);
            if (img) img.src = base64;
            if (type === 'photo') photoBase64 = base64; else signBase64 = base64;
            unifiedAutoSave();
        };
        reader.readAsDataURL(file);
    };

    window.showRowDirect = function (type) {
        const map = { '12th': ['row12th', 'btnAdd12th'], Grad: ['rowGrad', 'btnAddGrad'] };
        const [rowId, btnId] = map[type] || [];
        const row = rowId ? document.getElementById(rowId) : null;
        if (row) {
            row.style.display = 'grid';
            const streamEl = row.querySelector('.stream');
            if (streamEl) streamEl.required = true;
        }
        if (btnId) document.getElementById(btnId).style.display = 'none';
        if (!isRestoringData) {
            refreshProgramOptionsFromEducation();
            unifiedAutoSave();
        }
    };

    window.removeRowDirect = function (type) {
        if (type === '12th') {
            alert('12th education is compulsory and cannot be removed.');
            return;
        }
        if (!confirm('Remove this education row?')) return;
        const map = { Grad: ['rowGrad', 'btnAddGrad'] };
        const [rowId, btnId] = map[type] || [];
        const row = document.getElementById(rowId);
        if (row) {
            row.style.display = 'none';
            row.querySelectorAll('input, select').forEach(inp => {
                if (!inp.classList.contains('class-name')) {
                    inp.value = '';
                    if (inp.classList.contains('stream')) inp.required = false;
                }
            });
        }
        if (btnId) document.getElementById(btnId).style.display = 'inline-block';
        refreshProgramOptionsFromEducation();
        unifiedAutoSave();
    };

    window.calculateRowPercentage = function (el) {
        const row = el.closest('.edu-row');
        if (!row) return;
        const total = parseFloat(row.querySelector('.total-marks')?.value);
        const obtained = parseFloat(row.querySelector('.obtainedmarks')?.value);
        const pct = row.querySelector('.percentage');
        const grade = row.querySelector('.grade');
        if (!total || total <= 0) { if (pct) pct.value = ''; if (grade) grade.value = ''; return; }
        if (obtained > total) { alert('Obtained cannot exceed total'); el.value = ''; return; }
        const p = (obtained / total) * 100;
        if (pct) pct.value = p.toFixed(2);
        if (grade) {
            if (p >= 60) grade.value = 'First Division';
            else if (p >= 45) grade.value = 'Second Division';
            else if (p >= 33) grade.value = 'Third Division';
            else grade.value = 'Fail';
        }
        persistEducationDraftLocally();
    };

    function ensureSelectOption(selectEl, value) {
        if (!selectEl || !value) return;
        const exists = Array.from(selectEl.options).some(o => o.value === value);
        if (!exists) {
            const opt = document.createElement('option');
            opt.value = value;
            opt.textContent = value;
            selectEl.appendChild(opt);
        }
    }

    function fillDistrictDropdown(districtId, state, selectedDistrict = '') {
        const el = document.getElementById(districtId);
        if (!el) return;
        el.innerHTML = '<option value="">Select District</option>';
        if (!state || !indiaStatesDistricts[state]) {
            if (!cfg.formDisabled) el.disabled = true;
            return;
        }
        if (!cfg.formDisabled) el.disabled = false;
        [...indiaStatesDistricts[state]].sort().forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            el.appendChild(opt);
        });
        if (selectedDistrict) {
            ensureSelectOption(el, selectedDistrict);
            el.value = selectedDistrict;
        }
    }

    function onStateChange(stateId) {
        const districtId = stateId === 'txtPerState' ? 'txtPerDistrict' : 'txtCorDistrict';
        fillDistrictDropdown(districtId, val(stateId), '');
        if (!isRestoringData) unifiedAutoSave();
    }

    function setStateAndDistrict(stateId, districtId, stateVal, districtVal) {
        const stateEl = document.getElementById(stateId);
        if (!stateEl || !stateVal) return;
        ensureSelectOption(stateEl, stateVal);
        stateEl.value = stateVal;
        fillDistrictDropdown(districtId, stateVal, districtVal || '');
    }

    function fillBoardSelect(selectEl, options, placeholder, selectedValue = '') {
        if (!selectEl) return;
        selectEl.innerHTML = '';
        const blank = document.createElement('option');
        blank.value = '';
        blank.textContent = placeholder;
        selectEl.appendChild(blank);
        options.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            opt.title = name;
            selectEl.appendChild(opt);
        });
        if (selectedValue) {
            ensureSelectOption(selectEl, selectedValue);
            selectEl.value = selectedValue;
        }
    }

    function addOptionsToGroup(groupEl, names) {
        names.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            opt.title = name;
            groupEl.appendChild(opt);
        });
    }

    function fillUniversitySelect(selectEl, placeholder, selectedValue = '') {
        if (!selectEl) return;
        const cgUniversities = boardsUniversitiesData.chhattisgarh_universities || [];
        const otherUniversities = boardsUniversitiesData.universities || [];
        selectEl.innerHTML = '';
        const blank = document.createElement('option');
        blank.value = '';
        blank.textContent = placeholder;
        selectEl.appendChild(blank);

        if (cgUniversities.length) {
            const cgGroup = document.createElement('optgroup');
            cgGroup.label = 'Universities of Chhattisgarh';
            addOptionsToGroup(cgGroup, cgUniversities);
            selectEl.appendChild(cgGroup);
        }

        if (otherUniversities.length) {
            const otherGroup = document.createElement('optgroup');
            otherGroup.label = 'Other Universities of India';
            addOptionsToGroup(otherGroup, otherUniversities);
            selectEl.appendChild(otherGroup);
        }

        if (selectedValue) {
            ensureSelectOption(selectEl, selectedValue);
            selectEl.value = selectedValue;
        }
    }

    function initEducationBoardSelects(preserveValues = {}) {
        const schoolBoards = boardsUniversitiesData.school_boards || [];
        fillBoardSelect(
            document.getElementById('txtBoard10'),
            schoolBoards,
            'Select Board',
            preserveValues.txtBoard10 || '',
        );
        fillBoardSelect(
            document.getElementById('txtBoard12'),
            schoolBoards,
            'Select Board',
            preserveValues.txtBoard12 || '',
        );
        fillUniversitySelect(
            document.getElementById('txtBoardGrad'),
            'Select University',
            preserveValues.txtBoardGrad || '',
        );
    }

    async function loadBoardsUniversities() {
        if (!cfg.boardsDataUrl) return;
        try {
            const res = await fetch(cfg.boardsDataUrl);
            boardsUniversitiesData = await res.json();
        } catch (e) {
            console.error('Failed to load boards/universities data', e);
        }
        initEducationBoardSelects();
    }

    async function loadIndiaLocations() {
        if (!cfg.statesDataUrl) return;
        try {
            const res = await fetch(cfg.statesDataUrl);
            indiaStatesDistricts = await res.json();
        } catch (e) {
            console.error('Failed to load India states/districts', e);
            return;
        }
        const states = Object.keys(indiaStatesDistricts).sort();
        ['txtPerState', 'txtCorState'].forEach(stateId => {
            const el = document.getElementById(stateId);
            if (!el) return;
            const current = el.value;
            el.innerHTML = '<option value="">Select State</option>';
            states.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                opt.textContent = s;
                el.appendChild(opt);
            });
            if (current) {
                ensureSelectOption(el, current);
                el.value = current;
            }
            if (!cfg.formDisabled) {
                el.addEventListener('change', () => onStateChange(stateId));
            }
        });
    }

    window.copyAddress = function () {
        if (isRestoringData) return;
        const checked = document.getElementById('chkSameAddress').checked;
        if (checked) {
            setStateAndDistrict('txtCorState', 'txtCorDistrict', val('txtPerState'), val('txtPerDistrict'));
            [['txtPerCity', 'txtCorCity'], ['txtPerVillage', 'txtCorVillage'], ['txtPerPin', 'txtCorPin']].forEach(([src, dest]) => {
                const s = document.getElementById(src);
                const d = document.getElementById(dest);
                if (s && d) d.value = s.value;
            });
        } else {
            setStateAndDistrict('txtCorState', 'txtCorDistrict', '', '');
            ['txtCorCity', 'txtCorVillage', 'txtCorPin'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
        }
        unifiedAutoSave();
    };

    window.toggleDisabilityFields = function () {
        const ddl = document.getElementById('ddlDisabilityCertificate');
        const section = document.getElementById('disabilitySection');
        if (ddl && section) section.style.display = ddl.value === 'Yes' ? 'block' : 'none';
    };

    window.handlePreviewButtonVisibility = function () {
        updatePreviewButtonVisibility();
    };

    window.resetForm = function (e) {
        if (e) e.preventDefault();
        if (!confirm('Reset current step entries?')) return false;
        const step = getSteps()[current];
        step.querySelectorAll('input, select, textarea').forEach(c => {
            if (c.readOnly || c.disabled || c.id === 'txtRegNo') return;
            if (c.type === 'checkbox') c.checked = false;
            else if (c.tagName === 'SELECT') c.selectedIndex = 0;
            else c.value = '';
        });
        unifiedAutoSave();
        return false;
    };

    window.validateAndPreview = function () {
        if (cfg.formDisabled) return false;
        syncUploadBase64();
        const required = [
            'ddlProgramType', 'txtName', 'txtFather', 'txtMother', 'ddlGender', 'ddlCategory',
            'txtDOB', 'txtMobile', 'txtEmail', 'txtAadhaar',
            'txtPerState', 'txtPerDistrict', 'txtPerCity', 'txtPerVillage', 'txtPerPin',
            'txtCorState', 'txtCorDistrict', 'txtCorCity', 'txtCorVillage', 'txtCorPin',
            'txtBoard10', 'txtYear10', 'txtTotalMarks10', 'txtMarksObtained10',
            'txtBoard12', 'ddlStream12', 'txtYear12', 'txtTotalMarks12', 'txtMarksObtained12',
        ];
        for (const id of required) {
            const f = document.getElementById(id);
            if (f && !f.value.trim() && f.offsetWidth > 0) {
                f.classList.add('required-error');
                for (let j = 0; j < getSteps().length; j++) {
                    if (getSteps()[j].contains(f)) { showStep(j); break; }
                }
                f.scrollIntoView({ behavior: 'smooth', block: 'center' });
                alert('Please fill: ' + (f.labels?.[0]?.textContent || id));
                return false;
            }
        }
        const elig = getEducationEligibility();
        if (!elig.stream12) {
            alert('Please select stream for 12th.');
            showStep(2);
            return false;
        }
        if (elig.hasGrad && !elig.streamGrad) {
            alert('Please select stream for Graduation.');
            showStep(2);
            return false;
        }
        if (!val('ddlProgramLevel')) {
            alert('Please select a program type.');
            showStep(3);
            return false;
        }
        if (isBscProgram(val('ddlProgramType')) && !selectedBscGroup) {
            alert('Please select one B.Sc. subject group (Bio or Maths).');
            showStep(3);
            return false;
        }
        const checkedCourses = document.querySelectorAll('#courseTableBody input[type=checkbox]:checked');
        if (!checkedCourses.length) {
            alert('Please select at least one course.');
            showStep(3);
            return false;
        }
        if (!photoBase64 || !signBase64) { alert('Upload photo and signature.'); showStep(4); return false; }
        if (!document.getElementById('declarationCheck')?.checked) { alert('Accept declaration.'); showStep(5); return false; }

        const btn = document.getElementById('btnPreview');
        const prevLabel = btn ? btn.textContent : '';
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Saving...';
        }

        const data = collectFormData();
        fetch(cfg.saveDraftUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.csrfToken },
            body: JSON.stringify(data),
        })
            .then(r => r.json().then(res => ({ ok: r.ok, res })))
            .then(({ ok, res }) => {
                if (!ok || res.status !== 'DRAFT_SAVED') {
                    throw new Error(res.message || 'Could not save draft before preview.');
                }
                const appNo = res.application_no || data.ApplicationNo;
                if (!appNo) throw new Error('Application number was not generated.');
                const lbl = document.getElementById('lblAppNo');
                if (lbl) lbl.textContent = appNo;
                cfg.draftAppNo = appNo;
                window.location.href = cfg.previewUrl + '?app_no=' + encodeURIComponent(appNo);
            })
            .catch(err => {
                alert(err.message || 'Could not open preview. Please try again.');
            })
            .finally(() => {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = prevLabel || 'Preview Application';
                }
            });
        return false;
    };

    function normalizeDept(department) {
        return (department || '').trim().toLowerCase();
    }

    function findBscGroup(groupKey) {
        for (const section of bscSubjectGroups) {
            const match = (section.groups || []).find(g => g.key === groupKey);
            if (match) return { ...match, heading: section.heading };
        }
        return null;
    }

    function departmentInSelectedGroup(department, group) {
        if (!group || !department) return false;
        const dept = normalizeDept(department);
        return (group.departments || []).some(d => normalizeDept(d) === dept);
    }

    function rowInSelectedGroup(tr, group, groupKey) {
        if (!tr || !group || !groupKey) return false;
        const groupKeys = (tr.dataset.groupKeys || '').split(',').filter(Boolean);
        if (groupKeys.length) return groupKeys.includes(groupKey);
        return departmentInSelectedGroup(tr.dataset.department || '', group);
    }

    function applyCompulsoryToRow(tr, compulsory) {
        const chk = tr.querySelector('input[type=checkbox]');
        if (!chk) return;
        if (compulsory) {
            chk.checked = true;
            chk.disabled = true;
            tr.classList.add('group-locked');
            setCourseCompulsoryLabel(tr, true);
        } else {
            chk.disabled = false;
            tr.classList.remove('group-locked');
            setCourseCompulsoryLabel(tr, false);
        }
    }

    function setupBscGroupListeners() {
        const section = document.getElementById('bscGroupSection');
        if (!section || section.dataset.listenersBound === '1') return;
        section.dataset.listenersBound = '1';
        section.addEventListener('change', (e) => {
            if (!e.target.matches('input[name="bscSubjectGroup"]')) return;
            selectedBscGroup = e.target.value;
            applyBscGroupSelection(selectedBscGroup);
            updateSelectedGroupBadge();
            window._admissionAutoSave && window._admissionAutoSave();
        });
        section.addEventListener('click', (e) => {
            const radio = e.target.closest('input[name="bscSubjectGroup"]');
            if (!radio || cfg.formDisabled) return;
            selectedBscGroup = radio.value;
            applyBscGroupSelection(selectedBscGroup);
            updateSelectedGroupBadge();
        });
    }

    function renderBscSubjectGroups() {
        const panel = document.getElementById('bscSubjectGroups');
        if (!panel) return;
        if (!bscSubjectGroups.length) {
            panel.innerHTML = '<p class="bsc-group-hint">Loading subject groups...</p>';
            updateSelectedGroupBadge();
            return;
        }
        panel.innerHTML = bscSubjectGroups.map(section => `
            <div class="subject-group-section">
                <p class="subject-group-heading">${section.heading}</p>
                <div class="subject-group-options">
                    ${(section.groups || []).map(group => `
                        <label class="subject-group-option">
                            <input type="radio" name="bscSubjectGroup" value="${group.key}"
                                ${selectedBscGroup === group.key ? 'checked' : ''}
                                ${cfg.formDisabled ? 'disabled' : ''}>
                            <div>
                                <strong>${group.full_name || (section.heading + ' — ' + group.label)}</strong><br>
                                <span>${group.department_label}</span>
                            </div>
                        </label>
                    `).join('')}
                </div>
            </div>
        `).join('');
        setupBscGroupListeners();
        updateSelectedGroupBadge();
    }

    function isDscRow(tr) {
        return (tr.dataset.type2 || '').toUpperCase() === 'DSC' || tr.dataset.dsc === '1';
    }

    function setCourseCompulsoryLabel(tr, on) {
        const nameCell = tr.children[1];
        if (!nameCell) return;
        const existing = nameCell.querySelector('.compulsory-tag');
        if (on && !existing) {
            nameCell.insertAdjacentHTML(
                'beforeend',
                ' <small class="compulsory-tag" style="color:#166534;font-weight:600;">(Compulsory)</small>'
            );
        } else if (!on && existing) {
            existing.remove();
        }
    }

    function applyBscGroupSelection(groupKey) {
        const group = findBscGroup(groupKey);
        const groupName = getBscGroupFullName(groupKey);
        const showBsc = isBscProgram(val('ddlProgramType'));
        document.querySelectorAll('#courseTableBody tr').forEach(tr => {
            const chk = tr.querySelector('input[type=checkbox]');
            if (!chk || !tr.dataset.name) return;
            const isGroupCourse = tr.dataset.groupCourse === '1';
            const department = tr.dataset.department || '';
            const dbCompulsory = tr.dataset.dbCompulsory === '1';
            const groupColCell = showBsc ? tr.children[2] : null;

            if (!isGroupCourse) {
                tr.hidden = false;
                applyCompulsoryToRow(tr, dbCompulsory);
                if (groupColCell) groupColCell.innerHTML = '—';
                return;
            }

            if (!groupKey || !group) {
                tr.hidden = true;
                chk.checked = false;
                chk.disabled = true;
                tr.classList.remove('group-locked');
                setCourseCompulsoryLabel(tr, false);
                return;
            }

            const inGroup = rowInSelectedGroup(tr, group, groupKey);
            if (!inGroup) {
                tr.hidden = true;
                chk.checked = false;
                chk.disabled = true;
                tr.classList.remove('group-locked');
                setCourseCompulsoryLabel(tr, false);
                return;
            }

            tr.hidden = false;
            if (groupColCell && groupName) {
                groupColCell.innerHTML = `<span class="course-group-tag">${groupName}</span>`;
            }

            if (isDscRow(tr) || dbCompulsory) {
                applyCompulsoryToRow(tr, true);
            } else {
                chk.checked = false;
                applyCompulsoryToRow(tr, false);
            }
        });
        updateSelectedGroupBadge();
    }

    function resetBscGroupCoursesBeforeSelection() {
        document.querySelectorAll('#courseTableBody tr').forEach(tr => {
            const chk = tr.querySelector('input[type=checkbox]');
            if (!chk || !tr.dataset.name) return;
            if (tr.dataset.groupCourse === '1') {
                tr.hidden = true;
                chk.checked = false;
                chk.disabled = true;
                tr.classList.remove('group-locked');
                setCourseCompulsoryLabel(tr, false);
            }
        });
    }

    async function loadCourses(programType) {
        const tbody = document.getElementById('courseTableBody');
        if (!tbody) return;
        const resolvedProgramType = setProgramDropdown(programType) || normalizeProgramTypeForDropdown(programType);
        if (!resolvedProgramType) {
            tbody.innerHTML = '<tr><td colspan="4">Select a program type</td></tr>';
            return;
        }
        const showBsc = isBscProgram(resolvedProgramType);
        const colSpan = showBsc ? 5 : 4;
        updateBscGroupSectionVisibility(resolvedProgramType);
        tbody.innerHTML = `<tr><td colspan="${colSpan}">Loading...</td></tr>`;
        if (!showBsc) {
            selectedBscGroup = '';
        }
        const res = await fetch(
            cfg.coursesUrl
            + '?program_type=' + encodeURIComponent(resolvedProgramType)
            + '&_=' + Date.now()
        );
        const json = await res.json();
        if (json.resolved_program_type) {
            setProgramDropdown(json.resolved_program_type);
        }
        if (json.subject_groups?.length) {
            bscSubjectGroups = json.subject_groups;
        }
        if (showBsc) {
            setupBscGroupListeners();
            renderBscSubjectGroups();
        }
        tbody.innerHTML = '';
        json.courses.forEach((c) => {
            const tr = document.createElement('tr');
            const isGroupCourse = !!c.is_group_course;
            tr.dataset.name = c.course_name;
            tr.dataset.department = c.department || '';
            tr.dataset.type1 = c.course_type_1;
            tr.dataset.type2 = c.course_type_2;
            tr.dataset.dsc = c.is_dsc ? '1' : '0';
            tr.dataset.groupCourse = isGroupCourse ? '1' : '0';
            tr.dataset.groupDsc = c.is_group_dsc ? '1' : '0';
            tr.dataset.groupKeys = (c.group_keys || []).join(',');
            const compulsory = !!c.is_compulsory;
            tr.dataset.dbCompulsory = compulsory ? '1' : '0';
            const prelock = compulsory && !(showBsc && isGroupCourse);
            const checked = prelock ? 'checked' : '';
            const locked = prelock ? 'disabled' : '';
            const title = prelock ? ' title="Compulsory subject"' : '';
            if (showBsc && isGroupCourse) {
                tr.hidden = true;
            }
            const groupCell = showBsc ? '<td>—</td>' : '';
            tr.innerHTML = `<td><input type="checkbox" ${checked} ${locked}${title} onchange="window._admissionAutoSave && window._admissionAutoSave()"></td>
                <td>${c.course_name}${compulsory ? ' <small class="compulsory-tag" style="color:#166534;font-weight:600;">(Compulsory)</small>' : ''}</td>
                ${groupCell}
                <td>${c.course_type_1 || '-'}</td><td>${c.course_type_2 || 'N/A'}</td>`;
            tbody.appendChild(tr);
        });
        if (!json.courses.length) tbody.innerHTML = `<tr><td colspan="${colSpan}">No courses found</td></tr>`;
        if (showBsc) {
            if (selectedBscGroup) {
                const radio = document.querySelector(`input[name="bscSubjectGroup"][value="${selectedBscGroup}"]`);
                if (radio) radio.checked = true;
                applyBscGroupSelection(selectedBscGroup);
            } else {
                resetBscGroupCoursesBeforeSelection();
            }
        }
    }

    function eduClassName(edu) {
        return edu.ClassName || edu.className || edu.Class || '';
    }

    function eduField(edu, ...keys) {
        for (const key of keys) {
            if (edu[key] != null && edu[key] !== '') return edu[key];
        }
        return '';
    }

    function getDraftEducation(data) {
        const edu = data?.Education || data?.education;
        return Array.isArray(edu) ? edu : [];
    }

    function educationHasContent(eduList) {
        return eduList.some(edu =>
            eduField(edu, 'Board', 'board')
            || eduField(edu, 'Stream', 'stream')
            || eduField(edu, 'Year', 'year')
            || eduField(edu, 'TotalMarks', 'totalMarks', 'total_marks')
            || eduField(edu, 'Obtained', 'obtained', 'obtainedMarks')
        );
    }

    function eduRowId(edu) {
        const lower = eduClassName(edu).toLowerCase();
        if (lower.includes('grad') || lower.includes('bachelor') || lower.includes('degree')) {
            return 'rowGrad';
        }
        if (lower.includes('12') || lower.includes('xii') || lower.includes('inter')) {
            return 'row12th';
        }
        if (lower.includes('10') || lower.includes('ssc') || lower.includes('matric') || lower === 'x') {
            return 'row10th';
        }
        return '';
    }

    function restoreEducationFromDraft(data) {
        const education = getDraftEducation(data);
        if (!education.length) return false;

        const boardPreserve = {};
        education.forEach(edu => {
            const rowId = eduRowId(edu);
            if (rowId === 'row12th') showRowDirect('12th');
            if (rowId === 'rowGrad') showRowDirect('Grad');
            const boardVal = eduField(edu, 'Board', 'board');
            if (rowId === 'row10th') boardPreserve.txtBoard10 = boardVal;
            else if (rowId === 'row12th') boardPreserve.txtBoard12 = boardVal;
            else if (rowId === 'rowGrad') boardPreserve.txtBoardGrad = boardVal;
        });
        initEducationBoardSelects(boardPreserve);

        education.forEach(edu => {
            const rowId = eduRowId(edu);
            const row = rowId ? document.getElementById(rowId) : null;
            if (!row) return;
            const set = (cls, v) => {
                const el = row.querySelector('.' + cls);
                if (!el || v == null || v === '') return;
                const strVal = String(v);
                if (el.tagName === 'SELECT') ensureSelectOption(el, strVal);
                el.value = strVal;
            };
            set('class-name', eduClassName(edu));
            set('board', eduField(edu, 'Board', 'board'));
            set('stream', eduField(edu, 'Stream', 'stream'));
            set('duration', eduField(edu, 'Duration', 'duration'));
            set('year', eduField(edu, 'Year', 'year'));
            set('total-marks', eduField(edu, 'TotalMarks', 'totalMarks', 'total_marks'));
            set('obtainedmarks', eduField(edu, 'Obtained', 'obtained', 'obtainedMarks'));
            set('percentage', eduField(edu, 'Percentage', 'percentage'));
            set('grade', eduField(edu, 'Grade', 'grade'));
            const streamEl = row.querySelector('.stream');
            if (streamEl && streamEl.value) streamEl.required = true;
        });
        return educationHasContent(education);
    }

    function mergeDraftSources(serverData, localData) {
        if (!serverData && !localData) return null;
        const merged = { ...(serverData || {}) };
        if (!localData) return merged;

        const sameApp = !localData.ApplicationNo
            || !merged.ApplicationNo
            || localData.ApplicationNo === merged.ApplicationNo;

        if (sameApp && localData.ActiveStep != null) {
            merged.ActiveStep = localData.ActiveStep;
        }
        if (localData.DeclarationAccepted) {
            merged.DeclarationAccepted = localData.DeclarationAccepted;
        }

        const serverEdu = getDraftEducation(merged);
        const localEdu = getDraftEducation(localData);
        if (!educationHasContent(serverEdu) && educationHasContent(localEdu)) {
            merged.Education = localEdu;
            merged._educationMergedFromLocal = true;
        }

        return merged;
    }

    async function restoreData(data) {
        if (!data) return;
        const draftEducation = pickBestEducation(data);
        if (!Object.keys(data).length && !educationHasContent(draftEducation)) return;
        isRestoringData = true;
        const map = {
            txtName: data.FullName, txtFather: data.FatherName, txtMother: data.MotherName,
            ddlGender: data.Gender, ddlCategory: data.Category, txtNationality: data.Nationality,
            ddlReligion: data.Religion, ddlMaritalStatus: data.MaritalStatus, ddlBloodGroup: data.BloodGroup,
            txtDOB: data.DOB, txtMobile: data.Mobile, txtEmail: data.Email, txtAadhaar: data.Aadhaar,
            txtApaar: data.Apaar, txtDisabilityDetails: data.DisabilityDetails,
            txtDisabilityPercentage: data.DisabilityPercentage, txtDisabilityType: data.DisabilityType,
            ddlMinority: data.Minority, ddlMedium: data.Medium,
            txtPerCity: data.PermCity,
            txtPerVillage: data.PermVillage, txtPerPin: data.PermPinCode,
            txtCorCity: data.CorrCity,
            txtCorVillage: data.CorrVillage, txtCorPin: data.CorrPinCode,
        };
        Object.entries(map).forEach(([id, v]) => {
            const el = document.getElementById(id);
            if (!el || v == null || v === '') return;
            if (el.tagName === 'SELECT') {
                const exists = Array.from(el.options).some(o => o.value === v);
                if (!exists) {
                    const opt = document.createElement('option');
                    opt.value = v;
                    opt.textContent = v;
                    el.appendChild(opt);
                }
            }
            el.value = v;
        });

        const disabilityDdl = document.getElementById('ddlDisabilityCertificate');
        if (disabilityDdl) {
            disabilityDdl.value = data.HasDisability === 1 ? 'Yes' : (data.HasDisability === 0 ? 'No' : disabilityDdl.value);
            toggleDisabilityFields();
        }

        if (data.PermState) {
            setStateAndDistrict('txtPerState', 'txtPerDistrict', data.PermState, data.PermDistrict);
        }
        if (data.CorrState) {
            setStateAndDistrict('txtCorState', 'txtCorDistrict', data.CorrState, data.CorrDistrict);
        }

        const sameAddr = data.PermState && data.CorrState
            && data.PermState === data.CorrState
            && (data.PermDistrict || '') === (data.CorrDistrict || '')
            && (data.PermCity || '') === (data.CorrCity || '')
            && (data.PermVillage || '') === (data.CorrVillage || '')
            && (data.PermPinCode || '') === (data.CorrPinCode || '');
        const chkSame = document.getElementById('chkSameAddress');
        if (chkSame && sameAddr) chkSame.checked = true;

        if (data.PhotoBase64) {
            photoBase64 = data.PhotoBase64;
            const p = document.getElementById('imgPhotoPreview');
            if (p) p.src = photoBase64;
        }
        if (data.SignatureBase64) {
            signBase64 = data.SignatureBase64;
            const s = document.getElementById('imgSignPreview');
            if (s) s.src = signBase64;
        }
        if (data.ApplicationNo) applySavedAppNo(data.ApplicationNo);

        const educationSnapshot = pickBestEducation(data);
        restoreEducationFromDraft({ ...data, Education: educationSnapshot });

        refreshProgramOptionsFromEducation();

        const programType = normalizeProgramTypeForDropdown(
            data.ProgramType || cfg.initialProgramType || val('ddlProgramType'),
        );
        const programLevel = data.ProgramLevel || inferProgramLevel(programType) || cfg.initialProgramLevel;
        if (programLevel || programType) {
            const selection = initProgramDropdowns(programLevel, programType);
            refreshProgramOptionsFromEducation();
            const resolvedProgram = selection.programName || val('ddlProgramType') || programType;
            const filtered = getFilteredProgramsForLevel(val('ddlProgramLevel'));
            if (resolvedProgram && filtered.includes(resolvedProgram)) {
                selectedBscGroup = data.BScSubjectGroup || '';
                await loadCourses(resolvedProgram);
                updateBscGroupSectionVisibility(resolvedProgram);
                if (data.SelectedSubjects?.length) {
                    data.SelectedSubjects.forEach(s => {
                        document.querySelectorAll('#courseTableBody tr').forEach(tr => {
                            if (tr.dataset.name === s.name && tr.dataset.groupCourse !== '1') {
                                const chk = tr.querySelector('input[type=checkbox]');
                                if (chk && !chk.disabled) chk.checked = true;
                            }
                        });
                    });
                }
                if (selectedBscGroup) {
                    const radio = document.querySelector(`input[name="bscSubjectGroup"][value="${selectedBscGroup}"]`);
                    if (radio) radio.checked = true;
                    applyBscGroupSelection(selectedBscGroup);
                } else {
                    updateSelectedGroupBadge();
                }
            } else {
                clearCourseTable('Selected program is not available for your education stream');
            }
        }

        const declaration = document.getElementById('declarationCheck');
        if (declaration && data.DeclarationAccepted) declaration.checked = true;

        isRestoringData = false;

        if (educationHasContent(educationSnapshot)) {
            restoreEducationFromDraft({ Education: educationSnapshot });
            refreshProgramOptionsFromEducation();
        }

        const persisted = collectFormData();
        const savedEducation = educationHasContent(educationSnapshot)
            ? educationSnapshot
            : persisted.Education;
        persistDraftLocally({ ...persisted, ...data, Education: savedEducation });
        updateTabStatus();
        handlePreviewButtonVisibility();

        if (data._educationMergedFromLocal && !cfg.formDisabled) {
            saveDraftNow({ education: savedEducation, activeStep: data.ActiveStep }).catch(err => {
                console.error('Failed to sync merged education draft to server', err);
            });
        }

        if (data.ActiveStep != null && !Number.isNaN(Number(data.ActiveStep))) {
            let activeStep = parseInt(data.ActiveStep, 10);
            if ((data.WizardVersion || 1) < 2) {
                const legacyMap = { 0: 3, 1: 0, 2: 1, 3: 2 };
                if (legacyMap[activeStep] != null) activeStep = legacyMap[activeStep];
            }
            showStep(Math.min(Math.max(activeStep, 0), getSteps().length - 1));
            updateTabStatus();
            if (educationHasContent(educationSnapshot)) {
                restoreEducationFromDraft({ Education: educationSnapshot });
                refreshProgramOptionsFromEducation();
            }
        }
    }

    async function loadDraftData() {
        const embeddedData = getEmbeddedDraft();
        let apiData = null;

        if (cfg.loadDraftUrl) {
            try {
                let loadUrl = cfg.loadDraftUrl;
                const appNo = getAppNo() || cfg.draftAppNo || embeddedData?.ApplicationNo || '';
                if (appNo) loadUrl += '?app_no=' + encodeURIComponent(appNo);
                const res = await fetch(loadUrl);
                const json = await res.json();
                if (json.status === 'OK' && json.data && Object.keys(json.data).length) {
                    apiData = json.data;
                }
            } catch (e) {
                console.error('Failed to load draft from server', e);
            }
        }

        let localData = null;
        try {
            const raw = localStorage.getItem(getStorageKey());
            if (raw) localData = JSON.parse(raw);
        } catch (e) {
            console.error('Failed to parse local draft', e);
        }

        const base = {
            ...(embeddedData || {}),
            ...(apiData || {}),
        };
        if (!Object.keys(base).length && !localData) return null;

        const merged = mergeDraftSources(
            Object.keys(base).length ? base : null,
            localData,
        ) || localData || base;
        const bestEducation = pickBestEducation(apiData, embeddedData, localData, merged);
        if (bestEducation.length) {
            merged.Education = bestEducation;
        }
        return merged;
    }

    window._admissionAutoSave = unifiedAutoSave;

    document.addEventListener('DOMContentLoaded', async () => {
        window._admissionAutoSave = unifiedAutoSave;
        initBscSubjectGroups();
        setupBscGroupListeners();
        await Promise.all([loadIndiaLocations(), loadBoardsUniversities()]);

        const ddl = document.getElementById('ddlProgramType');
        const levelDdl = document.getElementById('ddlProgramLevel');
        if (!cfg.formDisabled && levelDdl) {
            levelDdl.addEventListener('change', () => {
                const rules = levelEligibilityMap();
                if (levelDdl.value && !rules[levelDdl.value]) {
                    alert('This program type is not available for your education details.');
                    levelDdl.value = '';
                    refreshProgramOptionsFromEducation();
                    return;
                }
                populateProgramNames(levelDdl.value);
                clearCourseTable('Select a program name');
                unifiedAutoSave();
            });
        }
        if (!cfg.formDisabled && ddl) {
            ddl.addEventListener('change', () => {
                updateBscGroupSectionVisibility(ddl.value);
                if (isBscProgram(ddl.value)) renderBscSubjectGroups();
                loadCourses(ddl.value).then(() => unifiedAutoSave());
            });
        }

        try {
            const embeddedDraft = getEmbeddedDraft();
            if (embeddedDraft) {
                await restoreData(embeddedDraft);
            }

            const draft = await loadDraftData();
            if (draft) {
                await restoreData(draft);
            }

            refreshProgramLevelDropdown();
            updateCourseStepHint();

            const initialSelection = initProgramDropdowns(
                cfg.initialProgramLevel,
                cfg.initialProgramType,
            );
            refreshProgramOptionsFromEducation();

            const programType = val('ddlProgramType') || initialSelection.programName;
            const programLevel = val('ddlProgramLevel') || initialSelection.level;
            if (programType && getEducationEligibility().canSelectUG) {
                const filtered = getFilteredProgramsForLevel(programLevel);
                if (filtered.includes(programType)) {
                    await loadCourses(programType);
                }
            }
        } catch (e) {
            console.error('Failed to restore admission draft', e);
        }

        bindEducationPersistence();

        if (!cfg.formDisabled) {
            document.addEventListener('input', e => {
                if (isRestoringData) return;
                if (e.target.closest('.edu-data-row')) return;
                if (['text', 'email', 'tel', 'number'].includes(e.target.type)) unifiedAutoSave();
            });
            document.addEventListener('change', e => {
                if (isRestoringData) return;
                if (e.target.closest('.edu-data-row')) return;
                unifiedAutoSave();
            });
            const chk = document.getElementById('declarationCheck');
            if (chk) {
                chk.addEventListener('change', () => {
                    handlePreviewButtonVisibility();
                    unifiedAutoSave();
                });
            }
            window.addEventListener('beforeunload', snapshotDraftToLocal);
            window.addEventListener('pagehide', snapshotDraftToLocal);
        }

        if (current === 0) {
            showStep(0);
            updateTabStatus();
        }
    });
})();