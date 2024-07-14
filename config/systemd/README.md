To use this service file:

1. Save it as `/etc/systemd/system/llm-vocabulary-reminder.service`.
2. Fill in the values for the environment variables.
3. Reload the systemd daemon: `sudo systemctl daemon-reload`
4. Start the service: `sudo systemctl start llm-vocabulary-reminder`
5. Enable the service to start on boot: `sudo systemctl enable llm-vocabulary-reminder`

Remember to replace the empty environment variable values with your actual tokens and keys before starting the service.
