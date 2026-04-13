import os
from erp_command_center import ERPCommandCenter

if __name__ == "__main__":
    # Ensure necessary folders exist
    os.makedirs("database/categories", exist_ok=True)
    os.makedirs("database/assets", exist_ok=True)
    os.makedirs("database/templates", exist_ok=True)
    os.makedirs("sessions", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    app = ERPCommandCenter()
    app.mainloop()
