document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const logsButton = document.getElementById('logsButton');
    const settingsButton = document.getElementById('settingsButton');
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
    
    sleepDurationInput.addEventListener('input', updateSleepDurationDisplay);
    
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
    
    // Tab switching
    logsButton.addEventListener('click', function() {
        logsContainer.style.display = 'flex';
        settingsContainer.style.display = 'none';
        logsButton.classList.add('active');
        settingsButton.classList.remove('active');
    });
    
    settingsButton.addEventListener('click', function() {
        logsContainer.style.display = 'none';
        settingsContainer.style.display = 'flex';
        settingsButton.classList.add('active');
        logsButton.classList.remove('active');
        loadSettings();
    });
    
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
    
    // Load settings from API
    function loadSettings() {
        fetch('/api/settings')
            .then(response => response.json())
            .then(data => {
                const huntarr = data.huntarr || {};
                const advanced = data.advanced || {};
                
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
            })
            .catch(error => console.error('Error loading settings:', error));
    }
    
    // Function to save settings
    function saveSettings() {
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
                alert('Settings saved successfully!');
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
                    alert('Settings reset to defaults.');
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
    saveSettingsButton.addEventListener('click', saveSettings);
    resetSettingsButton.addEventListener('click', resetSettings);
    
    saveSettingsBottomButton.addEventListener('click', saveSettings);
    resetSettingsBottomButton.addEventListener('click', resetSettings);
    
    // Event source for logs
    let eventSource;
    
    function connectEventSource() {
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
    logsElement.addEventListener('scroll', function() {
        // If we're at the bottom or near it (within 20px), ensure auto-scroll stays on
        const atBottom = (logsElement.scrollHeight - logsElement.scrollTop - logsElement.clientHeight) < 20;
        if (!atBottom && autoScrollCheckbox.checked) {
            // User manually scrolled up, disable auto-scroll
            autoScrollCheckbox.checked = false;
        }
    });
    
    // Re-enable auto-scroll when checkbox is checked
    autoScrollCheckbox.addEventListener('change', function() {
        if (this.checked) {
            scrollToBottom();
        }
    });
    
    // Initialize
    loadTheme();
    updateSleepDurationDisplay();
    connectEventSource();
});