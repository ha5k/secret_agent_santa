import ttkbootstrap as tb
from tkinter.constants import * #LEFT, padx, pady

# 1. Create the main window with a specific theme
root = tb.Window(themename="darkly")

# Optional: Set window title and dimensions
root.title("Welcome to SAS 2026")
root.geometry("400x200")

task_titles = ['TASK 1','TASK 2']
task_details = ['This is the definition of task 1', '...and the same for task 2']

def update_variable():
    current_value = counter_var.get()
    new_value = current_value + 1
    counter_var.set(new_value)
    label.config(text=f"Current Value: {new_value}")  # Manually update label text

counter_var = tb.IntVar(value=0)

    # 2. Create a Label to display the variable's value
    # While some widgets automatically update with a textvariable, a standard Label needs manual configuration or binding.

label = tb.Label(
        root,
        text=f"Current Value: {counter_var.get()}",
        font=("Helvetica", 16)
)

label.pack(pady=20)

# 2. Add widgets with bootstyle
# A button with 'success' primary color
b1 = tb.Button(root, text="Increment", command= update_variable(), bootstyle="success")
b1.pack(side=LEFT, padx=5, pady=10)

# A button with 'info' color and 'outline' style
b2 = tb.Button(root, text="Info Outline", bootstyle="info-outline")
b2.pack(side=LEFT, padx=5, pady=10)

# 3. Start the application
root.mainloop()
