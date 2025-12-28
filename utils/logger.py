class AppLogger:
    def __init__(self):
        self.logs = []
        self.status = "Prêt"
        self.active_task = None # None, 'step1', 'step2', 'step3', 'step4', 'step5'
        self.task_state = "IDLE" # IDLE, RUNNING, COMPLETED, ERROR
    
    def log(self, message):
        print(message)
        self.logs.append(message)
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]
        self.status = message
    
    def start_task(self, task_id):
        self.active_task = task_id
        self.task_state = "RUNNING"
        self.clear_logs()
        self.log(f"--- Démarrage {task_id} ---")

    def finish_task(self):
        self.task_state = "COMPLETED"
        self.log(f"--- Terminé {self.active_task} ---")
        # Do not reset active_task yet so frontend can see it finished

    def error_task(self, msg):
        self.task_state = "ERROR"
        self.log(f"ERREUR: {msg}")

    def clear_logs(self):
        self.logs = []
        self.status = "Démarrage..."

    def reset_state(self):
        """Resets the logger state to IDLE (e.g. on page reload)"""
        self.logs = []
        self.status = "Prêt"
        self.active_task = None
        self.task_state = "IDLE"

    def get_logs(self):
        return {
            "logs": self.logs,
            "status": self.status,
            "task_state": self.task_state,
            "active_task": self.active_task
        }

# Global instance
logger = AppLogger()
