document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const logsButton = document.getElementById('logsButton');
    const settingsButton = document.getElementById('settingsButton');
    const userButton = document.getElementById('userButton');
    const logsContainer = document.getElementById('logsContainer');
    const settingsContainer = document.getElementById('settingsContainer');
    const logsElement = document.getElementById('logs');
    const statusElement = document.getElementById('status');
    const clearLogsButton = document.getElementById('clearLogs');
    const autoScrollCheckbox = document.getElementById('autoScroll');
    const themeToggle = document.getElementById('themeToggle');
    const themeLabel = document.getElementById('themeLabel');
    
    // Settings form elements - Basic settings
    const huntMissingShowsInput = document.getElementById('hunt_missing_shows');
    const huntUpgradeEpisodesInput = document.getElementById('hunt_upgrade_episodes');
    const sleepDurationInput = document.getElementById('sleep_duration');
    const sleepDurationHoursSpan = document.getElementById('sleep_duration_hours');
    const stateResetIntervalInput = document.getElementById('state_reset_interval_hours');
    const monitoredOnlyInput = document.getElementById('monitored_only');
    const randomMissingInput = document.getElementById('random_missing');
    const randomUpgradesInput = document.getElementById('random_upgrades');
    const skipFutureEpisodesInput = document.getElementById('skip_future_episodes');
    const skipSeriesRefreshInput = document.getElementById('skip_series_refresh');
    
    // Settings form elements - Advanced settings
    const apiTimeoutInput = document.getElementById('api_timeout');
    const debugModeInput = document.getElementById('debug_mode');
    const commandWaitDelayInput = document.getElementById('command_wait_delay');
    const commandWaitAttemptsInput = document.getElementById('command_wait_attempts');
    const minimumDownloadQueueSizeInput = document.getElementById('minimum_download_queue_size');
    
    // Button elements for saving and resetting settings
    const saveSettingsButton = document.getElementById('saveSettings');
    const resetSettingsButton = document.getElementById('resetSettings');
    const saveSettingsBottomButton = document.getElementById('saveSettingsBottom');
    const resetSettingsBottomButton = document.getElementById('resetSettingsBottom');
    
    // Store original settings values
    let originalSettings = {};
    
    // Update sleep duration display
    function updateSleepDurationDisplay() {
        const seconds = parseInt(sleepDurationInput.value) || 900;
        let displayText = '';
        
        if (seconds < 60) {
            displayText = `${seconds} seconds`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            displayText = `≈ ${minutes} minute${minutes !== 1 ? 's' : ''}`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            if (minutes === 0) {
                displayText = `≈ ${hours} hour${hours !== 1 ? 's' : ''}`;
            } else {
                displayText = `≈ ${hours} hour${hours !== 1 ? 's' : ''} ${minutes} minute${minutes !== 1 ? 's' : ''}`;
            }
        }
        
        sleepDurationHoursSpan.textContent = displayText;
    }
    
    sleepDurationInput.addEventListener('input', function() {
        updateSleepDurationDisplay();
        checkForChanges();
    });
    
    // Theme management
    function loadTheme() {
        fetch('/api/settings/theme')
            .then(response => response.json())
            .then(data => {
                const isDarkMode = data.dark_mode || false;
                setTheme(isDarkMode);
                themeToggle.checked = isDarkMode;
                themeLabel.textContent = isDarkMode ? 'Dark Mode' : 'Light Mode';
            })
            .catch(error => console.error('Error loading theme:', error));
    }
    
    function setTheme(isDark) {
        if (isDark) {
            document.body.classList.add('dark-theme');
            themeLabel.textContent = 'Dark Mode';
        } else {
            document.body.classList.remove('dark-theme');
            themeLabel.textContent = 'Light Mode';
        }
    }
    
    themeToggle.addEventListener('change', function() {
        const isDarkMode = this.checked;
        setTheme(isDarkMode);
        
        fetch('/api/settings/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ dark_mode: isDarkMode })
        })
        .catch(error => console.error('Error saving theme:', error));
    });
    
    // Tab switching - Fixed to toggle visibility instead of redirecting
    if (logsButton && settingsButton && logsContainer && settingsContainer) {
        logsButton.addEventListener('click', function() {
            logsContainer.style.display = 'flex';
            settingsContainer.style.display = 'none';
            logsButton.classList.add('active');
            settingsButton.classList.remove('active');
            userButton.classList.remove('active');
        });
        
        settingsButton.addEventListener('click', function() {
            logsContainer.style.display = 'none';
            settingsContainer.style.display = 'flex';
            logsButton.classList.remove('active');
            settingsButton.classList.add('active');
            userButton.classList.remove('active');
            
            // Make sure settings are loaded when switching to settings tab
            loadSettings();
        });
        
        userButton.addEventListener('click', function() {
            window.location.href = '/user';
        });
    }
    
    // Log management
    clearLogsButton.addEventListener('click', function() {
        logsElement.innerHTML = '';
    });
    
    // Auto-scroll function
    function scrollToBottom() {
        if (autoScrollCheckbox.checked) {
            logsElement.scrollTop = logsElement.scrollHeight;
        }
    }
    
    // Function to check if settings have changed from original values
    function checkForChanges() {
        if (!originalSettings.huntarr) return; // Don't check if original settings not loaded
        
        let hasChanges = false;
        
        // Check Basic Settings
        if (parseInt(huntMissingShowsInput.value) !== originalSettings.huntarr.hunt_missing_shows) hasChanges = true;
        if (parseInt(huntUpgradeEpisodesInput.value) !== originalSettings.huntarr.hunt_upgrade_episodes) hasChanges = true;
        if (parseInt(sleepDurationInput.value) !== originalSettings.huntarr.sleep_duration) hasChanges = true;
        if (parseInt(stateResetIntervalInput.value) !== originalSettings.huntarr.state_reset_interval_hours) hasChanges = true;
        if (monitoredOnlyInput.checked !== originalSettings.huntarr.monitored_only) hasChanges = true;
        if (skipFutureEpisodesInput.checked !== originalSettings.huntarr.skip_future_episodes) hasChanges = true;
        if (skipSeriesRefreshInput.checked !== originalSettings.huntarr.skip_series_refresh) hasChanges = true;
        
        // Check Advanced Settings
        if (parseInt(apiTimeoutInput.value) !== originalSettings.advanced.api_timeout) hasChanges = true;
        if (debugModeInput.checked !== originalSettings.advanced.debug_mode) hasChanges = true;
        if (parseInt(commandWaitDelayInput.value) !== originalSettings.advanced.command_wait_delay) hasChanges = true;
        if (parseInt(commandWaitAttemptsInput.value) !== originalSettings.advanced.command_wait_attempts) hasChanges = true;
        if (parseInt(minimumDownloadQueueSizeInput.value) !== originalSettings.advanced.minimum_download_queue_size) hasChanges = true;
        if (randomMissingInput.checked !== originalSettings.advanced.random_missing) hasChanges = true;
        if (randomUpgradesInput.checked !== originalSettings.advanced.random_upgrades) hasChanges = true;
        
        // Enable/disable save buttons based on whether there are changes
        saveSettingsButton.disabled = !hasChanges;
        saveSettingsBottomButton.disabled = !hasChanges;
        
        // Apply visual indicator based on disabled state
        if (hasChanges) {
            saveSettingsButton.classList.remove('disabled-button');
            saveSettingsBottomButton.classList.remove('disabled-button');
        } else {
            saveSettingsButton.classList.add('disabled-button');
            saveSettingsBottomButton.classList.add('disabled-button');
        }
        
        return hasChanges;
    }
    
    // Add change event listeners to all form elements
    if (huntMissingShowsInput && huntUpgradeEpisodesInput && stateResetIntervalInput && 
        apiTimeoutInput && commandWaitDelayInput && commandWaitAttemptsInput && 
        minimumDownloadQueueSizeInput) {
        
        [huntMissingShowsInput, huntUpgradeEpisodesInput, stateResetIntervalInput, 
         apiTimeoutInput, commandWaitDelayInput, commandWaitAttemptsInput, 
         minimumDownloadQueueSizeInput].forEach(input => {
            input.addEventListener('input', checkForChanges);
        });
    }
    
    if (monitoredOnlyInput && randomMissingInput && randomUpgradesInput && 
        skipFutureEpisodesInput && skipSeriesRefreshInput && debugModeInput) {
        
        [monitoredOnlyInput, randomMissingInput, randomUpgradesInput, 
         skipFutureEpisodesInput, skipSeriesRefreshInput, debugModeInput].forEach(checkbox => {
            checkbox.addEventListener('change', checkForChanges);
        });
    }
    
    // Load settings from API
    function loadSettings() {
        if (!saveSettingsButton) return; // Skip if not on settings page
        
        fetch('/api/settings')
            .then(response => response.json())
            .then(data => {
                const huntarr = data.huntarr || {};
                const advanced = data.advanced || {};
                
                // Store original settings for comparison
                originalSettings = JSON.parse(JSON.stringify(data));
                
                // Fill form with current settings - Basic settings
                huntMissingShowsInput.value = huntarr.hunt_missing_shows !== undefined ? huntarr.hunt_missing_shows : 1;
                huntUpgradeEpisodesInput.value = huntarr.hunt_upgrade_episodes !== undefined ? huntarr.hunt_upgrade_episodes : 5;
                sleepDurationInput.value = huntarr.sleep_duration || 900;
                updateSleepDurationDisplay();
                stateResetIntervalInput.value = huntarr.state_reset_interval_hours || 168;
                monitoredOnlyInput.checked = huntarr.monitored_only !== false;
                skipFutureEpisodesInput.checked = huntarr.skip_future_episodes !== false;
                skipSeriesRefreshInput.checked = huntarr.skip_series_refresh === true;
                
                // Fill form with current settings - Advanced settings
                apiTimeoutInput.value = advanced.api_timeout || 60;
                debugModeInput.checked = advanced.debug_mode === true;
                commandWaitDelayInput.value = advanced.command_wait_delay || 1;
                commandWaitAttemptsInput.value = advanced.command_wait_attempts || 600;
                minimumDownloadQueueSizeInput.value = advanced.minimum_download_queue_size || -1;
                
                // Handle random settings
                randomMissingInput.checked = advanced.random_missing !== false;
                randomUpgradesInput.checked = advanced.random_upgrades !== false;
                
                // Initialize save buttons state
                saveSettingsButton.disabled = true;
                saveSettingsBottomButton.disabled = true;
                saveSettingsButton.classList.add('disabled-button');
                saveSettingsBottomButton.classList.add('disabled-button');
            })
            .catch(error => console.error('Error loading settings:', error));
    }
    
    // Function to save settings
    function saveSettings() {
        if (!checkForChanges()) {
            // If no changes, don't do anything
            return;
        }
        
        const settings = {
            huntarr: {
                hunt_missing_shows: parseInt(huntMissingShowsInput.value) || 0,
                hunt_upgrade_episodes: parseInt(huntUpgradeEpisodesInput.value) || 0,
                sleep_duration: parseInt(sleepDurationInput.value) || 900,
                state_reset_interval_hours: parseInt(stateResetIntervalInput.value) || 168,
                monitored_only: monitoredOnlyInput.checked,
                skip_future_episodes: skipFutureEpisodesInput.checked,
                skip_series_refresh: skipSeriesRefreshInput.checked
            },
            advanced: {
                api_timeout: parseInt(apiTimeoutInput.value) || 60,
                debug_mode: debugModeInput.checked,
                command_wait_delay: parseInt(commandWaitDelayInput.value) || 1,
                command_wait_attempts: parseInt(commandWaitAttemptsInput.value) || 600,
                minimum_download_queue_size: parseInt(minimumDownloadQueueSizeInput.value) || -1,
                random_missing: randomMissingInput.checked,
                random_upgrades: randomUpgradesInput.checked
            }
        };
        
        fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update original settings after successful save
                originalSettings = JSON.parse(JSON.stringify(settings));
                
                // Disable save buttons
                saveSettingsButton.disabled = true;
                saveSettingsBottomButton.disabled = true;
                saveSettingsButton.classList.add('disabled-button');
                saveSettingsBottomButton.classList.add('disabled-button');
                
                // Show success message
                if (data.changes_made) {
                    alert('Settings saved successfully and cycle restarted to apply changes!');
                } else {
                    alert('No changes detected.');
                }
            } else {
                alert('Error saving settings: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error saving settings:', error);
            alert('Error saving settings: ' + error.message);
        });
    }
    
    // Function to reset settings
    function resetSettings() {
        if (confirm('Are you sure you want to reset all settings to default values?')) {
            fetch('/api/settings/reset', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Settings reset to defaults and cycle restarted.');
                    loadSettings();
                } else {
                    alert('Error resetting settings: ' + (data.message || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error resetting settings:', error);
                alert('Error resetting settings: ' + error.message);
            });
        }
    }
    
    // Add event listeners to both button sets
    if (saveSettingsButton && resetSettingsButton && saveSettingsBottomButton && resetSettingsBottomButton) {
        saveSettingsButton.addEventListener('click', saveSettings);
        resetSettingsButton.addEventListener('click', resetSettings);
        
        saveSettingsBottomButton.addEventListener('click', saveSettings);
        resetSettingsBottomButton.addEventListener('click', resetSettings);
    }
    
    // Event source for logs
    let eventSource;
    
    function connectEventSource() {
        if (!logsElement) return; // Skip if not on logs page
        
        if (eventSource) {
            eventSource.close();
        }
        
        eventSource = new EventSource('/logs');
        
        eventSource.onopen = function() {
            statusElement.textContent = 'Connected';
            statusElement.className = 'status-connected';
        };
        
        eventSource.onerror = function() {
            statusElement.textContent = 'Disconnected';
            statusElement.className = 'status-disconnected';
            
            // Attempt to reconnect after 5 seconds
            setTimeout(connectEventSource, 5000);
        };
        
        eventSource.onmessage = function(event) {
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            
            // Add appropriate class for log level
            if (event.data.includes(' - INFO - ')) {
                logEntry.classList.add('log-info');
            } else if (event.data.includes(' - WARNING - ')) {
                logEntry.classList.add('log-warning');
            } else if (event.data.includes(' - ERROR - ')) {
                logEntry.classList.add('log-error');
            } else if (event.data.includes(' - DEBUG - ')) {
                logEntry.classList.add('log-debug');
            }
            
            logEntry.textContent = event.data;
            logsElement.appendChild(logEntry);
            
            // Auto-scroll to bottom if enabled
            scrollToBottom();
        };
    }
    
    // Observe scroll event to detect manual scrolling
    if (logsElement) {
        logsElement.addEventListener('scroll', function() {
            // If we're at the bottom or near it (within 20px), ensure auto-scroll stays on
            const atBottom = (logsElement.scrollHeight - logsElement.scrollTop - logsElement.clientHeight) < 20;
            if (!atBottom && autoScrollCheckbox.checked) {
                // User manually scrolled up, disable auto-scroll
                autoScrollCheckbox.checked = false;
            }
        });
    }
    
    // Re-enable auto-scroll when checkbox is checked
    if (autoScrollCheckbox) {
        autoScrollCheckbox.addEventListener('change', function() {
            if (this.checked) {
                scrollToBottom();
            }
        });
    }
    
    // Initialize
    loadTheme();
    if (sleepDurationInput) {
        updateSleepDurationDisplay();
    }
    
    // Check if we're on the settings page by checking URL path
    const isSettingsPage = window.location.pathname === '/settings';
    
    // If on settings page, show settings initially
    if (isSettingsPage && logsContainer && settingsContainer) {
        logsContainer.style.display = 'none';
        settingsContainer.style.display = 'flex';
        logsButton.classList.remove('active');
        settingsButton.classList.add('active');
        userButton.classList.remove('active');
        loadSettings();
    } else {
        // On any other page, load settings only if we're on the main page
        if (window.location.pathname === '/' && settingsContainer) {
            settingsContainer.style.display = 'none';
            loadSettings();
        }
    }
    
    if (logsElement) {
        connectEventSource();
    }
});