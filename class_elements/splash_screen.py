import customtkinter as ctk
from PIL import Image
import time
from utils.path_utils import resource_path


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Loading...")
        self.geometry("500x500")
        self.resizable(False, False)
        self.iconbitmap(resource_path("icons/butterfly_icon.ico"))

        # Load Image
        self.bg_image = ctk.CTkImage(light_image=Image.open(resource_path("icons/butterfly_splash.png")),
                                     size=(500, 500))

        # Background Label
        self.bg_label = ctk.CTkLabel(self, image=self.bg_image, text="", corner_radius=0, fg_color="#dbd7d1")
        self.bg_label.place(relwidth=1, relheight=1)

        # Frame for Progress and Timer Labels (just above the progress bar)
        label_frame = ctk.CTkFrame(self, fg_color="#dbd7d1", corner_radius=0, height=5)
        label_frame.place(relx=0.5, rely=1, y=-3, anchor="s", relwidth=1.0)  # Move it closer to the bar

        # Progress Label (Left)
        self.progress_label = ctk.CTkLabel(label_frame, text="Starting up...",
                                        font=("Helvetica", 11),
                                        fg_color="#dbd7d1",
                                        corner_radius=0)
        self.progress_label.pack(side="left", padx=10)  # Slight nudge lower

        # Timer Label (Right)
        self.timer_label = ctk.CTkLabel(label_frame, text="Elapsed Time: 0s",
                                        font=("Helvetica", 11),
                                        fg_color="#dbd7d1",
                                        corner_radius=0)
        self.timer_label.pack(side="right", padx=10)  # Same nudge

        # Progress Bar (Bottom of window)
        self.progress_bar = ctk.CTkProgressBar(self, corner_radius=0, height=8)
        self.progress_bar.place(x=0, rely=1.0, relwidth=1.0, anchor="sw")
        self.progress_bar.set(0)

        # Timer Logic
        self.start_time = time.time()
        self.timer_running = True
        self.update_timer()

        self.update_idletasks()


    def update_progress(self, progress, message):
        """Update the progress bar and label text dynamically."""
        self.progress_bar.set(progress)
        
        # Force redraw to clear ghost characters
        self.progress_label.configure(text="")               # Clear old text
        self.update_idletasks()
        
        self.progress_label.configure(text=message)          # Now set correct message
        self.update_idletasks()                              # Refresh UI again


    def update_timer(self):
        """Update the elapsed time and refresh UI at regular intervals."""
        if not hasattr(self, 'timer_running') or not self.timer_running:
            return  # Prevent AttributeError if called after destruction

        elapsed_time = time.time() - self.start_time
        self.timer_label.configure(text=f"Elapsed Time: {elapsed_time:.0f}s")
        self.after(100, self.update_timer)  # Update every 100ms


    def stop_timer(self):
        """Stops the timer when loading completes."""
        self.timer_running = False  # Prevent further updates
        elapsed_time = time.time() - self.start_time
        self.timer_label.configure(text=f"Total Time: {elapsed_time:.0f}s")
