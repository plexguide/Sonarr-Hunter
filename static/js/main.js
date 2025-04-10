document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const homeButton = document.getElementById('homeButton');
    const logsButton = document.getElementById('logsButton');
    const settingsButton = document.getElementById('settingsButton');
    const userButton = document.getElementById('userButton');
    const homeContainer = document.getElementById('homeContainer');
    const logsContainer = document.getElementById('logsContainer');
    const settingsContainer = document.getElementById('settingsContainer');
    const logsElement = document.getElementById('logs');
    const statusElement = document.getElementById('status');
    const clearLogsButton = document.getElementById('clearLogs');
    const autoScrollCheckbox = document.getElementById('autoScroll');
    const themeToggle = document.getElementById('themeToggle');
    const themeLabel = document.getElementById('themeLabel');
    
    // App tabs
    const appTabs = document.querySelectorAll('.app-tab');
    const appSettings = document.querySelectorAll('.app-settings');
    
    // Connection status elements on home page
    const sonarrHomeStatus = document.getElementById('sonarrHomeStatus');
    const radarrHomeStatus = document.getElementById('radarrHomeStatus');
    const lidarrHomeStatus = document.getElementById('lidarrHomeStatus');
    const readarrHomeStatus = document.getElementById('readarrHomeStatus');
    
    // Current selected app
    let currentApp = 'sonarr';
    
    // App settings - Sonarr
    const sonarrApiUrlInput = document.getElementById('sonarr_api_url');
    const sonarrApiKeyInput = document.getElementById('sonarr_api_key');
    const sonarrConnectionStatus = document.getElementById('sonarrConnectionStatus');
    const testSonarrConnectionButton = document.getElementById('testSonarrConnection');
    
    // Settings form elements - Basic settings (Sonarr)
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
    
    // Track which apps are configured
    const configuredApps = {
        sonarr: false,
        radarr: false,
        lidarr: false,
        readarr: false
    };
    
    // App selection handler
    appTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const app = this.dataset.app;
            
            // If it's already the active app, do nothing
            if (app === currentApp) return;
            
            // Update active tab
            appTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Update active settings panel if on settings page
            if (settingsContainer && settingsContainer.style.display !== 'none') {
                appSettings.forEach(s => s.style.display = 'none');
                document.getElementById(`${app}Settings`).style.display = 'block';
            }
            
            // Update current app
            currentApp = app;
            
            // Load settings for this app
            loadSettings(app);
            
            // For logs, we need to refresh the log stream
            if (logsElement && logsContainer && logsContainer.style.display !== 'none') {
                // Clear the logs first
                logsElement.innerHTML = '';
                
                // Update connection status based on configuration
                if (statusElement) {
                    if (configuredApps[app]) {
                        statusElement.textContent = 'Connected';
                        statusElement.className = 'status-connected';
                    } else {
                        statusElement.textContent = 'Disconnected';
                        statusElement.className = 'status-disconnected';
                    }
                }
                
                // Reconnect the event source only if app is configured
                if (configuredApps[app]) {
                    connectEventSource(app);
                }
            }
        });
    });
    
    // Update sleep duration display
    function updateSleepDurationDisplay() {
        if (!sleepDurationInput || !sleepDurationHoursSpan) return;
        
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
    
    if (sleepDurationInput) {
        sleepDurationInput.addEventListener('input', function() {
            updateSleepDurationDisplay();
            checkForChanges();
        });
    }
    
    // Theme management
    function loadTheme() {
        fetch('/api/settings/theme')
            .then(response => response.json())
            .then(data => {
                const isDarkMode = data.dark_mode || false;
                setTheme(isDarkMode);
                if (themeToggle) themeToggle.checked = isDarkMode;
                if (themeLabel) themeLabel.textContent = isDarkMode ? 'Dark Mode' : 'Light Mode';
            })
            .catch(error => console.error('Error loading theme:', error));
    }
    
    function setTheme(isDark) {
        if (isDark) {
            document.body.classList.add('dark-theme');
            if (themeLabel) themeLabel.textContent = 'Dark Mode';
        } else {
            document.body.classList.remove('dark-theme');
            if (themeLabel) themeLabel.textContent = 'Light Mode';
        }
    }
    
    if (themeToggle) {
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
    }
    
    // Get user's name for welcome message
    function getUserInfo() {
        // This is a placeholder - in a real implementation, you'd likely have an API
        // to get the current user's information
        const username = document.getElementById('username');
        if (username) {
            username.textContent = 'User'; // Default placeholder
        }
    }
    
    // Update connection status on the home page
    function updateHomeConnectionStatus() {
        // Sonarr status
        if (sonarrHomeStatus) {
            if (configuredApps.sonarr) {
                sonarrHomeStatus.textContent = 'Configured';
                sonarrHomeStatus.className = 'connection-badge connected';
            } else {
                sonarrHomeStatus.textContent = 'Not Configured';
                sonarrHomeStatus.className = 'connection-badge not-connected';
            }
        }
        
        // Radarr status
        if (radarrHomeStatus) {
            if (configuredApps.radarr) {
                radarrHomeStatus.textContent = 'Configured';
                radarrHomeStatus.className = 'connection-badge connected';
            } else {
                radarrHomeStatus.textContent = 'Not Configured';
                radarrHomeStatus.className = 'connection-badge not-connected';
            }
        }
        
        // Lidarr status
        if (lidarrHomeStatus) {
            if (configuredApps.lidarr) {
                lidarrHomeStatus.textContent = 'Configured';
                lidarrHomeStatus.className = 'connection-badge connected';
            } else {
                lidarrHomeStatus.textContent = 'Not Configured';
                lidarrHomeStatus.className = 'connection-badge not-connected';
            }
        }
        
        // Readarr status
        if (readarrHomeStatus) {
            if (configuredApps.readarr) {
                readarrHomeStatus.textContent = 'Configured';
                readarrHomeStatus.className = 'connection-badge connected';
            } else {
                readarrHomeStatus.textContent = 'Not Configured';
                readarrHomeStatus.className = 'connection-badge not-connected';
            }
        }
    }
    
    // Update logs connection status
    function updateLogsConnectionStatus() {
        if (statusElement) {
            if (configuredApps[currentApp]) {
                statusElement.textContent = 'Connected';
                statusElement.className = 'status-connected';
            } else {
                statusElement.textContent = 'Disconnected';
                statusElement.className = 'status-disconnected';
            }
        }
    }
    
    // Tab switching - Toggle visibility of containers
    if (homeButton && logsButton && settingsButton && homeContainer && logsContainer && settingsContainer) {
        homeButton.addEventListener('click', function() {
            homeContainer.style.display = 'flex';
            logsContainer.style.display = 'none';
            settingsContainer.style.display = 'none';
            homeButton.classList.add('active');
            logsButton.classList.remove('active');
            settingsButton.classList.remove('active');
            userButton.classList.remove('active');
            
            // Update connection status on home page
            updateHomeConnectionStatus();
        });
        
        logsButton.addEventListener('click', function() {
            homeContainer.style.display = 'none';
            logsContainer.style.display = 'flex';
            settingsContainer.style.display = 'none';
            homeButton.classList.remove('active');
            logsButton.classList.add('active');
            settingsButton.classList.remove('active');
            userButton.classList.remove('active');
            
            // Update the connection status based on configuration
            updateLogsConnectionStatus();
            
            // Reconnect to logs for the current app if configured
            if (logsElement && configuredApps[currentApp]) {
                connectEventSource(currentApp);
            }
        });
        
        settingsButton.addEventListener('click', function() {
            homeContainer.style.display = 'none';
            logsContainer.style.display = 'none';
            settingsContainer.style.display = 'flex';
            homeButton.classList.remove('active');
            logsButton.classList.remove('active');
            settingsButton.classList.add('active');
            userButton.classList.remove('active');
            
            // Show the settings for the current app
            appSettings.forEach(s => s.style.display = 'none');
            document.getElementById(`${currentApp}Settings`).style.display = 'block';
            
            // Make sure settings are loaded
            loadSettings(currentApp);
        });
        
        userButton.addEventListener('click', function() {
            window.location.href = '/user';
        });
    }
    
    // Log management
    if (clearLogsButton) {
        clearLogsButton.addEventListener('click', function() {
            if (logsElement) logsElement.innerHTML = '';
        });
    }
    
    // Auto-scroll function
    function scrollToBottom() {
        if (autoScrollCheckbox && autoScrollCheckbox.checked && logsElement) {
            logsElement.scrollTop = logsElement.scrollHeight;
        }
    }
    
    // Test connection for Sonarr
    if (testSonarrConnectionButton) {
        testSonarrConnectionButton.addEventListener('click', function() {
            const apiUrl = sonarrApiUrlInput.value;
            const apiKey = sonarrApiKeyInput.value;
            
            if (!apiUrl || !apiKey) {
                alert('Please enter both API URL and API Key before testing the connection.');
                return;
            }
            
            // Test API connection
            if (sonarrConnectionStatus) {
                sonarrConnectionStatus.textContent = 'Testing...';
                sonarrConnectionStatus.className = 'connection-badge';
            }
            
            fetch('/api/test-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    app: 'sonarr',
                    api_url: apiUrl,
                    api_key: apiKey
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (sonarrConnectionStatus) {
                        sonarrConnectionStatus.textContent = 'Connected';
                        sonarrConnectionStatus.className = 'connection-badge connected';
                    }
                    
                    // Update configuration status
                    configuredApps.sonarr = true;
                    
                    // Update home page status
                    if (sonarrHomeStatus) {
                        sonarrHomeStatus.textContent = 'Connected';
                        sonarrHomeStatus.className = 'connection-badge connected';
                    }
                } else {
                    if (sonarrConnectionStatus) {
                        sonarrConnectionStatus.textContent = 'Connection Failed';
                        sonarrConnectionStatus.className = 'connection-badge not-connected';
                    }
                    
                    // Update configuration status
                    configuredApps.sonarr = false;
                    
                    alert(`Connection failed: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error testing connection:', error);
                if (sonarrConnectionStatus) {
                    sonarrConnectionStatus.textContent = 'Connection Error';
                    sonarrConnectionStatus.className = 'connection-badge not-connected';
                }
                
                // Update configuration status
                configuredApps.sonarr = false;
                
                alert('Error testing connection: ' + error.message);
            });
        });
    }
    
    // Function to check if settings have changed from original values
    function checkForChanges() {
        if (!originalSettings.huntarr) return false; // Don't check if original settings not loaded
        
        let hasChanges = false;
        
        // API connection settings
        if (sonarrApiUrlInput && sonarrApiUrlInput.value !== originalSettings.api_url) hasChanges = true;
        if (sonarrApiKeyInput && sonarrApiKeyInput.value !== originalSettings.api_key) hasChanges = true;
        
        // Check Basic Settings
        if (huntMissingShowsInput && parseInt(huntMissingShowsInput.value) !== originalSettings.huntarr.hunt_missing_shows) hasChanges = true;
        if (huntUpgradeEpisodesInput && parseInt(huntUpgradeEpisodesInput.value) !== originalSettings.huntarr.hunt_upgrade_episodes) hasChanges = true;
        if (sleepDurationInput && parseInt(sleepDurationInput.value) !== originalSettings.huntarr.sleep_duration) hasChanges = true;
        if (stateResetIntervalInput && parseInt(stateResetIntervalInput.value) !== originalSettings.huntarr.state_reset_interval_hours) hasChanges = true;
        if (monitoredOnlyInput && monitoredOnlyInput.checked !== originalSettings.huntarr.monitored_only) hasChanges = true;
        if (skipFutureEpisodesInput && skipFutureEpisodesInput.checked !== originalSettings.huntarr.skip_future_episodes) hasChanges = true;
        if (skipSeriesRefreshInput && skipSeriesRefreshInput.checked !== originalSettings.huntarr.skip_series_refresh) hasChanges = true;
        
        // Check Advanced Settings
        if (apiTimeoutInput && parseInt(apiTimeoutInput.value) !== originalSettings.advanced.api_timeout) hasChanges = true;
        if (debugModeInput && debugModeInput.checked !== originalSettings.advanced.debug_mode) hasChanges = true;
        if (commandWaitDelayInput && parseInt(commandWaitDelayInput.value) !== originalSettings.advanced.command_wait_delay) hasChanges = true;
        if (commandWaitAttemptsInput && parseInt(commandWaitAttemptsInput.value) !== originalSettings.advanced.command_wait_attempts) hasChanges = true;
        if (minimumDownloadQueueSizeInput && parseInt(minimumDownloadQueueSizeInput.value) !== originalSettings.advanced.minimum_download_queue_size) hasChanges = true;
        if (randomMissingInput && randomMissingInput.checked !== originalSettings.advanced.random_missing) hasChanges = true;
        if (randomUpgradesInput && randomUpgradesInput.checked !== originalSettings.advanced.random_upgrades) hasChanges = true;
        
        // Enable/disable save buttons based on whether there are changes
        if (saveSettingsButton && saveSettingsBottomButton) {
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
        }
        
        return hasChanges;
    }
    
    // Add change event listeners to all form elements
    if (sonarrApiUrlInput && sonarrApiKeyInput) {
        sonarrApiUrlInput.addEventListener('input', checkForChanges);
        sonarrApiKeyInput.addEventListener('input', checkForChanges);
    }
    
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
    function loadSettings(app = 'sonarr') {
        fetch('/api/settings')
            .then(response => response.json())
            .then(data => {
                const huntarr = data.huntarr || {};
                const advanced = data.advanced || {};
                
                // Store original settings for comparison
                originalSettings = JSON.parse(JSON.stringify(data));
                
                // Connection settings for the current app (currently only sonarr is implemented)
                if (app === 'sonarr' && sonarrApiUrlInput && sonarrApiKeyInput) {
                    sonarrApiUrlInput.value = data.api_url || '';
                    sonarrApiKeyInput.value = data.api_key || '';
                    
                    // Update configured status for sonarr
                    configuredApps.sonarr = !!(data.api_url && data.api_key);
                    
                    // Update connection status
                    if (sonarrConnectionStatus) {
                        if (data.api_url && data.api_key) {
                            sonarrConnectionStatus.textContent = 'Configured';
                            sonarrConnectionStatus.className = 'connection-badge connected';
                        } else {
                            sonarrConnectionStatus.textContent = 'Not Configured';
                            sonarrConnectionStatus.className = 'connection-badge not-connected';
                        }
                    }
                    
                    // Sonarr-specific settings
                    if (huntMissingShowsInput) {
                        huntMissingShowsInput.value = huntarr.hunt_missing_shows !== undefined ? huntarr.hunt_missing_shows : 1;
                    }
                    if (huntUpgradeEpisodesInput) {
                        huntUpgradeEpisodesInput.value = huntarr.hunt_upgrade_episodes !== undefined ? huntarr.hunt_upgrade_episodes : 5;
                    }
                    if (sleepDurationInput) {
                        sleepDurationInput.value = huntarr.sleep_duration || 900;
                        updateSleepDurationDisplay();
                    }
                    if (stateResetIntervalInput) {
                        stateResetIntervalInput.value = huntarr.state_reset_interval_hours || 168;
                    }
                    if (monitoredOnlyInput) {
                        monitoredOnlyInput.checked = huntarr.monitored_only !== false;
                    }
                    if (skipFutureEpisodesInput) {
                        skipFutureEpisodesInput.checked = huntarr.skip_future_episodes !== false;
                    }
                    if (skipSeriesRefreshInput) {
                        skipSeriesRefreshInput.checked = huntarr.skip_series_refresh === true;
                    }
                    
                    // Advanced settings
                    if (apiTimeoutInput) {
                        apiTimeoutInput.value = advanced.api_timeout || 60;
                    }
                    if (debugModeInput) {
                        debugModeInput.checked = advanced.debug_mode === true;
                    }
                    if (commandWaitDelayInput) {
                        commandWaitDelayInput.value = advanced.command_wait_delay || 1;
                    }
                    if (commandWaitAttemptsInput) {
                        commandWaitAttemptsInput.value = advanced.command_wait_attempts || 600;
                    }
                    if (minimumDownloadQueueSizeInput) {
                        minimumDownloadQueueSizeInput.value = advanced.minimum_download_queue_size || -1;
                    }
                    if (randomMissingInput) {
                        randomMissingInput.checked = advanced.random_missing !== false;
                    }
                    if (randomUpgradesInput) {
                        randomUpgradesInput.checked = advanced.random_upgrades !== false;
                    }
                }
                
                // Update home page connection status
                updateHomeConnectionStatus();
                
                // Update log connection status if on logs page
                if (logsContainer && logsContainer.style.display !== 'none') {
                    updateLogsConnectionStatus();
                }
                
                // Initialize save buttons state
                if (saveSettingsButton && saveSettingsBottomButton) {
                    saveSettingsButton.disabled = true;
                    saveSettingsBottomButton.disabled = true;
                    saveSettingsButton.classList.add('disabled-button');
                    saveSettingsBottomButton.classList.add('disabled-button');
                }
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
            app_type: currentApp,
            api_url: sonarrApiUrlInput ? sonarrApiUrlInput.value : '',
            api_key: sonarrApiKeyInput ? sonarrApiKeyInput.value : '',
            huntarr: {
                hunt_missing_shows: huntMissingShowsInput ? parseInt(huntMissingShowsInput.value) || 0 : 0,
                hunt_upgrade_episodes: huntUpgradeEpisodesInput ? parseInt(huntUpgradeEpisodesInput.value) || 0 : 0,
                sleep_duration: sleepDurationInput ? parseInt(sleepDurationInput.value) || 900 : 900,
                state_reset_interval_hours: stateResetIntervalInput ? parseInt(stateResetIntervalInput.value) || 168 : 168,
                monitored_only: monitoredOnlyInput ? monitoredOnlyInput.checked : true,
                skip_future_episodes: skipFutureEpisodesInput ? skipFutureEpisodesInput.checked : true,
                skip_series_refresh: skipSeriesRefreshInput ? skipSeriesRefreshInput.checked : false
            },
            advanced: {
                debug_mode: debugModeInput ? debugModeInput.checked : false,
                command_wait_delay: commandWaitDelayInput ? parseInt(commandWaitDelayInput.value) || 1 : 1,
                command_wait_attempts: commandWaitAttemptsInput ? parseInt(commandWaitAttemptsInput.value) || 600 : 600,
                minimum_download_queue_size: minimumDownloadQueueSizeInput ? parseInt(minimumDownloadQueueSizeInput.value) || -1 : -1,
                random_missing: randomMissingInput ? randomMissingInput.checked : true,
                random_upgrades: randomUpgradesInput ? randomUpgradesInput.checked : true,
                api_timeout: apiTimeoutInput ? parseInt(apiTimeoutInput.value) || 60 : 60
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
                
                // Update configuration status based on API URL and API key
                configuredApps.sonarr = !!(settings.api_url && settings.api_key);
                
                // Update connection status
                if (sonarrConnectionStatus) {
                    if (settings.api_url && settings.api_key) {
                        sonarrConnectionStatus.textContent = 'Configured';
                        sonarrConnectionStatus.className = 'connection-badge connected';
                    } else {
                        sonarrConnectionStatus.textContent = 'Not Configured';
                        sonarrConnectionStatus.className = 'connection-badge not-connected';
                    }
                }
                
                // Update home page connection status
                updateHomeConnectionStatus();
                
                // Update logs connection status
                updateLogsConnectionStatus();
                
                // Disable save buttons
                if (saveSettingsButton && saveSettingsBottomButton) {
                    saveSettingsButton.disabled = true;
                    saveSettingsBottomButton.disabled = true;
                    saveSettingsButton.classList.add('disabled-button');
                    saveSettingsBottomButton.classList.add('disabled-button');
                }
                
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
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ app: currentApp })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Settings reset to defaults and cycle restarted.');
                    loadSettings(currentApp);
                    
                    // Update home page connection status
                    updateHomeConnectionStatus();
                    
                    // Update logs connection status
                    updateLogsConnectionStatus();
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
    
    function connectEventSource(app = 'sonarr') {
        if (!logsElement) return; // Skip if not on logs page
        if (!configuredApps[app]) return; // Skip if app not configured
        
        if (eventSource) {
            eventSource.close();
        }
        
        eventSource = new EventSource(`/logs?app=${app}`);
        
        eventSource.onopen = function() {
            if (statusElement) {
                statusElement.textContent = 'Connected';
                statusElement.className = 'status-connected';
            }
        };
        
        eventSource.onerror = function() {
            if (statusElement) {
                statusElement.textContent = 'Disconnected';
                statusElement.className = 'status-disconnected';
            }
            
            // Attempt to reconnect after 5 seconds if app is still configured
            setTimeout(() => {
                if (configuredApps[app]) {
                    connectEventSource(app);
                }
            }, 5000);
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
            if (!atBottom && autoScrollCheckbox && autoScrollCheckbox.checked) {
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
    
    // Get user info for welcome page
    getUserInfo();
    
    // Load settings for initial app
    loadSettings(currentApp);
    
    // Check if we're on the settings page by URL path
    const path = window.location.pathname;
    
    // Show proper content based on path or hash
    if (path === '/settings') {
        // Show settings page
        if (homeContainer) homeContainer.style.display = 'none';
        if (logsContainer) logsContainer.style.display = 'none';
        if (settingsContainer) settingsContainer.style.display = 'flex';
        
        if (homeButton) homeButton.classList.remove('active');
        if (logsButton) logsButton.classList.remove('active');
        if (settingsButton) settingsButton.classList.add('active');
        if (userButton) userButton.classList.remove('active');
    } else if (path === '/') {
        // Default to home page
        if (homeContainer) homeContainer.style.display = 'flex';
        if (logsContainer) logsContainer.style.display = 'none';
        if (settingsContainer) settingsContainer.style.display = 'none';
        
        if (homeButton) homeButton.classList.add('active');
        if (logsButton) logsButton.classList.remove('active');
        if (settingsButton) settingsButton.classList.remove('active');
        if (userButton) userButton.classList.remove('active');
        
        // Update connection status on home page
        updateHomeConnectionStatus();
    }
    
    // Connect to logs if we're on the logs page and the current app is configured
    if (logsElement && logsContainer && logsContainer.style.display !== 'none' && configuredApps[currentApp]) {
        connectEventSource(currentApp);
    }
});