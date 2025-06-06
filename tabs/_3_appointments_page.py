import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
from class_elements.profile_card import ProfileCard
from class_elements.treeview_styling_light import style_treeview_light
from class_elements.photo_upload_popup import PhotoUploadPopup
from upload_server.qr_helper import generate_upload_qr
from utils.path_utils import resource_path
from datetime import datetime
from PIL import Image
import re
import os
import shutil
import sqlite3


class AppointmentsPage:
    def __init__(self, parent, main_app, data_manager):
        self.main_app = main_app
        self.client_id = None  # Store selected client ID
        self.sort_orders = {}  # Store sort order (ascending/descending) for each column
        self.data_manager = data_manager

        # Create Main frame (holds both Treeview and Details frame)
        main_frame = ctk.CTkFrame(parent)
        main_frame.pack(fill="both", expand=True, padx=10)

        # Configure grid columns for sizing
        main_frame.columnconfigure(0, weight=1) # Search frame
        main_frame.columnconfigure(1, weight=1) # Create appt frame
        main_frame.columnconfigure(2, weight=1) # Update/Photo buttons
        main_frame.columnconfigure(3, weight=1) # Delete button 
        main_frame.columnconfigure(4, weight=8) # Details frame
        main_frame.rowconfigure(1, weight=1)    # Allow frames to stretch vertically

        # Create Frame for search box
        search_frame = ctk.CTkFrame(main_frame, fg_color="#563A9C")
        search_frame.grid(row=0, column=0, sticky="nw", padx=(0, 0), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)  # Ensure the combobox expands properly

        # Create search label
        search_label = ctk.CTkLabel(search_frame, text="Change Client:", font=("Helvetica", 14, "bold"), fg_color="transparent", text_color="#ebebeb")
        search_label.grid(row=0, column=0, sticky="w", padx=10)

        # Update the Combobox to Match Styling
        self.client_var = ctk.StringVar(value="Select a client...")
        self.client_combobox = ctk.CTkComboBox(
            search_frame, 
            variable=self.client_var, 
            values=[], 
            command=self.on_client_selected, 
            width=180,
            text_color="#000000"
        )
        self.client_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=2)  # Stretch across grid
        self.client_combobox.configure(text_color="#797e82")

        # Keybinds for combobox functionality
        self.client_combobox.bind("<KeyRelease>", self.filter_clients)
        self.client_combobox.bind("<FocusOut>", self.restore_placeholder)
        self.client_combobox.bind("<Button-1>", self.clear_placeholder)  # Click event
        self.client_combobox.bind("<FocusIn>", self.clear_placeholder)  # Keyboard focus

        # Load images for buttons
        add_appt = ctk.CTkImage(Image.open(resource_path("icons/add.png")), size=(24, 24))
        edit_appt = ctk.CTkImage(Image.open(resource_path("icons/edit_appt.png")), size=(24, 24))
        add_imgs = ctk.CTkImage(Image.open(resource_path("icons/add_photo_alt.png")), size=(24, 24))
        delete_appt = ctk.CTkImage(Image.open(resource_path("icons/delete.png")), size=(24, 24))

        # Create Frame for Create Button
        create_frame = ctk.CTkFrame(main_frame)
        create_frame.grid(row=0, column=1, sticky="e", padx=(0, 5), pady=(0, 10))

        self.create_button = ctk.CTkButton(create_frame, 
                                           text="",
                                           image=add_appt,
                                           command=self.create_appointment, 
                                           width=24)
        self.create_button.pack(side="left", padx=(5, 5))  # Align right

        # Update & Photos Buttons (Pinned to Right)
        button_frame = ctk.CTkFrame(main_frame)  # Small frame to hold buttons
        button_frame.grid(row=0, column=2, sticky="e", padx=(5, 5), pady=(0, 10))  # Pin to right

        self.update_button = ctk.CTkButton(button_frame, 
                                           text="",
                                           image=edit_appt, 
                                           command=self.update_appointment, 
                                           width=24)
        self.update_button.pack(side="left", padx=(5, 5))  # Align right

        self.photos_button = ctk.CTkButton(button_frame, 
                                        text="",
                                        image=add_imgs, 
                                        command=self.add_photos, 
                                        width=24)
        self.photos_button.pack(side="left", padx=(0, 5))  # Align right

        # Update & Photos Buttons (Pinned to Right)
        delete_frame = ctk.CTkFrame(main_frame)  # Small frame to hold buttons
        delete_frame.grid(row=0, column=3, sticky="e", padx=(5, 5), pady=(0, 10))  # Pin to right

        self.delete_button = ctk.CTkButton(delete_frame, 
                                        text="",
                                        hover_color="#FF4444",  # Red hover color for delete
                                        image=delete_appt, 
                                        command=self.delete_appointment, 
                                        width=24)
        self.delete_button.pack(side="left", padx=(5, 5))  # Align right

        # Create Treeview Frame
        treeview_frame = ctk.CTkFrame(main_frame)
        treeview_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=(0, 5), pady=(0, 10))

        # Apply treeview styling
        style_treeview_light("Appointments.Treeview")

        # Treeview widget for appointments
        columns = ("date", "type", "treatment", "price", "photos")
        self.appointments_table = ttk.Treeview(treeview_frame, selectmode="extended", columns=columns, show="headings", height=10, style="Appointments.Treeview")
        self.appointments_table.pack(side="left", fill="both", expand=True)
        self.appointments_table.tag_configure("odd", background="#b3b3b3")   # MID_GRAY
        self.appointments_table.tag_configure("even", background="#ebebeb")    # SOFT_WHITE
        self.appointments_table.bind("<ButtonRelease-1>", self.on_appointment_select)
        self.appointments_table.bind("<Double-1>", self.on_double_click_edit_appointment)
        self.appointments_table.bind("<Delete>", self.delete_appointment)
        self.appointments_table.bind("<BackSpace>", self.delete_appointment)

        # Create clickable column headers
        for col in columns:
            self.appointments_table.heading(col, text=col.capitalize(), command=lambda c=col: self.sort_appointments_treeview(c))

        # Add vertical scrollbar
        scrollbar_y = ttk.Scrollbar(treeview_frame, orient="vertical", command=self.appointments_table.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.appointments_table.configure(yscrollcommand=scrollbar_y.set)

        # Set initial column widths
        self.set_column_widths()

        # Bind the Treeview to resize event
        self.appointments_table.bind("<Configure>", lambda event: self.set_column_widths())

        # Bind selection event to Treeview
        self.appointments_table.bind("<ButtonRelease-1>", self.on_appointment_select)

        # Create Details Frame
        self.details_frame = ctk.CTkFrame(main_frame, fg_color="#563A9C")
        self.details_frame.grid(row=0, rowspan=2, column=4, sticky="nsew", padx=(10, 0), pady=(0, 10))
        self.details_frame.grid_propagate(False)  # Prevent auto-expanding

        # Configure grid inside details_frame
        self.details_frame.columnconfigure(0, weight=1, minsize=50)  # Minimum width
        self.details_frame.columnconfigure(1, weight=0)  # No expansion beyond this
        self.details_frame.rowconfigure(1, weight=1)  # Allow the textboxes to expand vertically

        # Create Label/Textbox for "All Appointment Notes"
        self.notes_label = ctk.CTkLabel(self.details_frame, text="Treatment Notes", font=("Helvetica", 16, "bold"), fg_color="transparent", text_color="#ebebeb")
        self.notes_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.all_notes_textbox = tk.Text(self.details_frame,  
                                         font=("Helvetica", 18), 
                                         wrap="word", 
                                         bd=0, 
                                         border=0, 
                                         borderwidth=0, 
                                         highlightthickness=0,
                                         foreground="#000000",
                                         background="#ebebeb")
        self.all_notes_textbox.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.all_notes_textbox.configure(state="disabled")  # Disable editing


    def on_client_selected(self, selected_client):
        """Triggered when a client is selected from the combobox."""
        if not selected_client or selected_client == "No matches found":
            self.client_combobox.configure(text_color="#797e82")  # Placeholder color
            self.client_combobox.set("Select a client...")  # Restore placeholder
            return  # Exit early, don't process selection

        with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM clients WHERE full_name = ?", (selected_client,))
            result = cursor.fetchone()

        if result:
            self.client_id = result[0]  # Store the client ID
            print(f"Selected Client: {selected_client} (ID: {self.client_id})")

            self.main_app.tabs["Clients"].select_client_by_id(self.client_id)


    def set_column_widths(self):
        """Adjust column widths dynamically based on the current Treeview width."""
        total_width = self.appointments_table.winfo_width()

        # Set column widths as percentages of the total width
        self.appointments_table.column("date", width=int(total_width * 0.10), minwidth=150)
        self.appointments_table.column("type", width=int(total_width * 0.10), minwidth=200)
        self.appointments_table.column("treatment", width=int(total_width * 0.55), minwidth=200)
        self.appointments_table.column("price", width=int(total_width * 0.10), minwidth=150)
        self.appointments_table.column("photos", width=int(total_width * 0.12), minwidth=120)


    def filter_clients(self, event):
        """Dynamically update the client dropdown based on user input."""
        query = self.client_combobox.get().strip()
        if query:
            self.client_combobox.configure(text_color="#000000")
            with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT full_name FROM clients WHERE full_name LIKE ? LIMIT 10", (f"%{query}%",))
                matches = [row[0] for row in cursor.fetchall()]

            self.client_combobox.configure(values=matches if matches else ["No matches found"])
        else:
            self.client_combobox.configure(values=[])
        self.client_combobox.focus()


    def restore_placeholder(self, event=None):
        """Restore the placeholder text if no valid client is selected when focus is lost."""
        current_text = self.client_var.get().strip()

        if not current_text or current_text == "No matches found":
            self.client_combobox.set("Select a client...")  # Reset placeholder
            self.client_combobox.configure(text_color="#797e82")


    def clear_placeholder(self, event=None):
        """Clear the placeholder text when the user clicks or focuses on the combobox."""
        if self.client_var.get() == "Select a client...":  # Only clear if it's the placeholder
            self.client_combobox.set("")  # Clear text to allow typing
            self.client_combobox.configure(text_color="#797e82")


    def load_client_appointments(self, client_id):
        if self.client_id != client_id:
            self.client_combobox.set("Select a client...")
            self.client_combobox.configure(text_color="#797e82")
        else:
            self.client_combobox.configure(text_color="#000000")

        self.client_id = client_id
        self.appointments_table.delete(*self.appointments_table.get_children())
        self.all_notes_textbox.configure(state="normal")
        self.all_notes_textbox.delete("1.0", "end")
        self.all_notes_textbox.configure(state="disabled")

        try:
            with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, date, type, treatment, price, photos_taken, treatment_notes 
                    FROM appointments 
                    WHERE client_id = ?
                    ORDER BY date DESC
                """, (client_id,))
                appointments = cursor.fetchall()

            for index, row in enumerate(appointments):
                appointment_id, date, type, treatment, price, photos_taken, treatment_notes = row
                self.appointments_table.insert("", "end", iid=str(appointment_id), values=(date, type, treatment, price, photos_taken))

            self.update_alternating_colors()
            self.load_all_treatment_notes()
        except Exception as e:
            print(f"Error loading appointments: {e}")


    def on_appointment_select(self, event):
        """Handle selection of multiple appointments and update the All Notes textbox in real-time."""
        selected_items = self.appointments_table.selection()  # Get ALL selected appointments
        if not selected_items:
            return

        # Configure Text Styles (Headers: 11px, Notes: 10px)
        self.all_notes_textbox.tag_configure("header", font=("Helvetica", 22, "bold"))
        self.all_notes_textbox.tag_configure("body", font=("Helvetica", 18))
        self.all_notes_textbox.tag_configure("divider", font=("Helvetica", 10))
        self.all_notes_textbox.tag_configure("highlight", background="#563A9C", foreground="#ebebeb")  # Highlighted selection

        # Enable Editing & Clear Existing Notes
        self.all_notes_textbox.configure(state="normal")
        self.all_notes_textbox.delete("1.0", "end")

        jump_to_index = None  # Store the first occurrence for scrolling

        for item in selected_items:
            appointment_id = self.get_selected_appointment_id(item)  
            appointment_data = self.appointments_table.item(item)["values"]

            if not appointment_data:
                print(f"⚠ Skipping Appointment ID {appointment_id}: No data found.")
                continue  

            # Extract fields
            date = appointment_data[0]
            type = appointment_data[1]
            treatment = appointment_data[2]
            price = appointment_data[3]
            photos_taken = appointment_data[4]

            # Debugging statements
            print(f"Appointment ID:     {appointment_id}")
            print(f"Date:               {date}")
            print(f"Type:               {type}") 
            print(f"Treatment:          {treatment}") 
            print(f"Price:              {price}")
            print(f"photos Taken?:       {photos_taken}")
            print(f"----------------------------")

            if len(selected_items) > 1:  # Multiple selection: Compile only the selected appointments' notes
                print("\nMultiple Appointments Selected:")

                appointment_id = int(self.get_selected_appointment_id(item))  # Ensure correct ID type
                print(f"Fetching notes for appointment_id: {appointment_id}")

                # Fetch from DB
                try:
                    with sqlite3.connect(self.data_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT treatment_notes FROM appointments WHERE id = ?", (appointment_id,))
                        result = cursor.fetchone()
                        treatment_notes = result[0] if result and result[0] else "(No notes found)"
                except Exception as e:
                    print(f"Failed to fetch notes for ID {appointment_id}: {e}")
                    treatment_notes = "(Error retrieving notes)"

                # Dynamic Divider Logic (Match longest text)
                max_length = max(len(date), len(treatment) - 2)
                if max_length > 35:
                    max_length = 35
                divider_line = "━" * max(max_length + 3, 1)

                # Insert formatted text with correct tags
                start_index = self.all_notes_textbox.index("end")  # Store where this note starts
                self.all_notes_textbox.insert("end", f"{divider_line}\n", "divider")  # Top Divider
                self.all_notes_textbox.insert("end", f"{treatment}\n", "header")  # Treatment (Header)
                self.all_notes_textbox.insert("end", f"{date}\n", "header")  # Date (Header)
                self.all_notes_textbox.insert("end", f"{divider_line}\n\n", "divider")  # Bottom Divider
                self.all_notes_textbox.insert("end", f"{treatment_notes}\n\n", "body")  # Notes (Body)

                # Store first match to jump to
                if jump_to_index is None:
                    jump_to_index = start_index

            else:  # Single selection: Displays ALL compiled appointment notes
                self.load_all_treatment_notes()
                
                # Get the selected appointment note to jump to
                selected_item = selected_items[0]
                selected_data = self.appointments_table.item(selected_item)["values"]
                if selected_data:
                    selected_date = selected_data[0]
                    selected_treatment = selected_data[2]

                    # Find the first occurrence of the note
                    search_text = f"{selected_treatment}\n{selected_date}"
                    jump_to_index = self.all_notes_textbox.search(search_text, "1.0", stopindex="end", nocase=True)

                    # Apply highlight **ONLY IF ONE APPOINTMENT IS SELECTED**
                    if jump_to_index:
                        end_index = f"{jump_to_index.split('.')[0]}.end"
                        self.all_notes_textbox.tag_add("highlight", jump_to_index, end_index)
                        # print(f" Highlighted note at index: {jump_to_index}")

        # Scroll to first matching note (if found) & ensure it appears at the **top**
        if jump_to_index:
            # print(f"{float(jump_to_index.split('.')[0])} / {float(self.all_notes_textbox.index('end').split('.')[0])} = {float(jump_to_index.split('.')[0]) / float(self.all_notes_textbox.index('end').split('.')[0])}")
            self.all_notes_textbox.yview_moveto((float(jump_to_index.split('.')[0]) - 2) / float(self.all_notes_textbox.index('end').split('.')[0]))
            # print(f" Jumped to note at index: {jump_to_index}")

        # Disable Editing Again
        self.all_notes_textbox.configure(state="disabled")


    def load_all_treatment_notes(self):
        """Load all treatment notes for the selected client, sorted by most recent appointment."""
        
        if not self.client_id:
            print("No client selected. Cannot load notes.")
            return

        with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, treatment, treatment_notes 
                FROM appointments 
                WHERE client_id = ? 
                AND treatment_notes IS NOT NULL 
                AND treatment_notes != ''
                ORDER BY date DESC
            """, (self.client_id,))
            all_notes = cursor.fetchall()

        # Clear existing notes
        self.all_notes_textbox.configure(state="normal")  # Enable Editing
        self.all_notes_textbox.delete("1.0", "end")

        # Configure Text Styles (Headers: 14px, Notes: 12px)
        self.all_notes_textbox.tag_configure("header", font=("Helvetica", 22, "bold"))
        self.all_notes_textbox.tag_configure("body", font=("Helvetica", 18))
        self.all_notes_textbox.tag_configure("divider", font=("Helvetica", 10))

        # Compile formatted notes with dynamic dividers
        for date, treatment, notes in all_notes:
            max_length = max(len(date), len(treatment) - 2)
            if max_length > 35:
                max_length = 35
            divider_line = "━" * max(max_length + 3, 1)

            self.all_notes_textbox.insert("end", f"{divider_line}\n", "divider")  # Top Divider
            self.all_notes_textbox.insert("end", f"{treatment}\n", "header")  # Treatment (Header)
            self.all_notes_textbox.insert("end", f"{date}\n", "header")  # Date (Header)
            self.all_notes_textbox.insert("end", f"{divider_line}\n\n", "divider")  # Bottom Divider
            self.all_notes_textbox.insert("end", f"{notes}\n\n", "body")  # Notes (Body)

        if not all_notes:
            self.all_notes_textbox.insert("1.0", "No treatment notes available.", "body")

        self.all_notes_textbox.configure(state="disabled")  # Disable Again
        

    def clear_appointments(self):
        """Clear all rows in the appointments Treeview and treatment notes."""
        self.appointments_table.delete(*self.appointments_table.get_children())
        self.all_notes_textbox.configure(state="normal")  # Enable Editing
        self.all_notes_textbox.delete("1.0", "end")
        self.all_notes_textbox.configure(state="disabled")  # Disable Again

        # Reset Appointments ComboBox to Placeholder
        self.client_combobox.set("Select a client...")
        self.client_combobox.configure(text_color="#797e82")  # Ensure placeholder color


    def sort_appointments_treeview(self, column):
        """Sort the appointments TreeView by column."""
        data = [(self.appointments_table.set(item, column), item) for item in self.appointments_table.get_children()]

        # Toggle sort order (ascending/descending)
        reverse = self.sort_orders.get(column, False)
        self.sort_orders[column] = not reverse  # Flip the sorting order for next click

        try:
            if column == "date":
                data.sort(key=lambda x: datetime.strptime(x[0], "%m/%d/%Y"), reverse=reverse)
            elif column == "type":
                data.sort(key=lambda x: datetime.strptime(x[0], "%I:%M %p"), reverse=reverse)
            elif column == "price":
                data.sort(key=lambda x: float(x[0].replace("$", "")), reverse=reverse)
            else:
                data.sort(key=lambda x: x[0].lower(), reverse=reverse)  # Alphabetical sorting
        except ValueError:
            data.sort(key=lambda x: x[0], reverse=reverse)

        # Rearrange items in sorted order
        for index, (val, item) in enumerate(data):
            self.appointments_table.move(item, "", index)

        self.update_alternating_colors()

        # Update the column heading to trigger sorting when clicked again
        self.appointments_table.heading(column, command=lambda c=column: self.sort_appointments_treeview(c))


    def create_appointment(self):
        """Open a dialog to create a new appointment."""
        print(f"Inside create_appointment - current client_id: {self.client_id}")

        if not self.client_id:
            print("No client selected. Cannot create appointment.")
            return
        print("Creating new appointment for Client ID:", self.client_id)
        
        # CREATE POP-UP WINDOW --> Create Appointment
        self.appointment_window = ctk.CTkToplevel()
        self.appointment_window.title("Create Appointment")
        self.appointment_window.geometry("500x400")
        self.appointment_window.resizable(True, True)

        # FORCE POP-UP AS TOP WINDOW & DISABLE MAIN WINDOW
        self.appointment_window.transient(self.main_app)  # Make it child of main app
        self.appointment_window.grab_set()  # Disable main window interaction
        self.appointment_window.focus_force()  # Force focus on the popup

        # Ensure proper window stretching
        self.appointment_window.grid_rowconfigure((0, 2), weight=1)
        self.appointment_window.grid_rowconfigure(1, weight=1)
        self.appointment_window.grid_columnconfigure(0, weight=1)

        # Row 0 [appt_window]: Create pop-up main frame
        self.pop_main_frame = ctk.CTkFrame(self.appointment_window)
        self.pop_main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ###########################################################
        ### ---------- POP_MAIN_FRAME CONTENTS BELOW ---------- ###
        ###########################################################

        # Ensure `pop_main_frame` expands properly
        self.pop_main_frame.columnconfigure((0, 2, 4), weight=1)  # Entry weights
        self.pop_main_frame.columnconfigure((1, 3, 5), weight=1)  # Label weights
        self.pop_main_frame.rowconfigure((0, 1, 2), weight=1)

        # Row 0 [pop_main_frame]: DATE Label/Entry
        ctk.CTkLabel(self.pop_main_frame, text="Date", anchor="w", width=70).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.date_entry = ctk.CTkEntry(self.pop_main_frame, placeholder_text="MM/DD/YYYY")
        self.date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.date_entry.bind("<Return>", lambda event: (self.format_date(), self.focus_next_widget(event)))
        self.date_entry.bind("<FocusOut>", lambda event: self.format_date())

        # Row 0 [pop_main_frame]: TYPE Label/Entry
        ctk.CTkLabel(self.pop_main_frame, text="Type", anchor="w", width=70).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.type_entry = ctk.CTkEntry(self.pop_main_frame, placeholder_text="Facial, etc.")
        self.type_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.type_entry.bind("<Return>", lambda event: self.focus_next_widget(event))
        self.type_entry.bind("<FocusOut>")

        # Row 0 [pop_main_frame]: PRICE Label/Entry
        ctk.CTkLabel(self.pop_main_frame, text="Price", anchor="w", width=70).grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.price_entry = ctk.CTkEntry(self.pop_main_frame, placeholder_text="$0.00")
        self.price_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        self.price_entry.bind("<Return>", lambda event: (self.format_price(), self.focus_next_widget(event)))
        self.price_entry.bind("<FocusOut>", lambda event: self.format_price())

        # Row 1 [pop_main_frame]: TREATMENT Label/Entry
        ctk.CTkLabel(self.pop_main_frame, text="Treatment", anchor="w", width=102).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.treatment_entry = ctk.CTkEntry(self.pop_main_frame, placeholder_text="Treatment Name")
        self.treatment_entry.grid(row=1, column=1, columnspan=5, padx=5, pady=5, sticky="ew")

        ###########################################################
        ### ---------- POP_MAIN_FRAME CONTENTS ABOVE ---------- ###
        ###########################################################

        # Row 1 [appt_window]: Create NOTES Frame
        self.notes_frame = ctk.CTkFrame(self.appointment_window)
        self.notes_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

       # Ensure the notes frame stretches properly
        self.notes_frame.grid_rowconfigure(0, weight=1)
        self.notes_frame.grid_columnconfigure(0, weight=1)

        # Row 1 [notes_frame]: NOTES Label/Textbox
        self.notes_label = ctk.CTkLabel(self.notes_frame, text="Notes").grid(row=0, column=0, sticky="w", padx=5)
        self.current_notes_textbox = ctk.CTkTextbox(self.notes_frame, corner_radius=0, wrap="word", fg_color="#ebebeb")
        self.current_notes_textbox.grid(row=1, column=0, sticky="nsew")

        # Row 2 [appt_window]: Save Button
        self.save_button = ctk.CTkButton(self.notes_frame, text="Save", command=self.save_new_appointment)
        self.save_button.grid(row=2, column=0, pady=10)


    def save_new_appointment(self):
        """Save the new appointment to the database."""
        # EXTRACT --> PACK data from entry boxes into variables
        date = self.date_entry.get().strip()
        type = self.type_entry.get().strip()
        treatment = self.treatment_entry.get().strip()
        price = self.price_entry.get().strip()
        treatment_notes = self.current_notes_textbox.get("1.0", "end").strip()

        # VALIDATION CHECK --> Date, Treatment, and Price are REQUIRED
        missing_fields = []
        if not date:
            missing_fields.append("- Date")
        if not treatment:
            missing_fields.append("- Treatment")
        if not price:
            missing_fields.append("- Price")

        if missing_fields:
            # SHOW WARNING MESSAGE and return to popup window
            messagebox.showwarning("Missing Fields", f"Please fill out the following required fields:\n\n{chr(10).join(missing_fields)}")
            return

        # Apply CORRECT FORMATTING to all entry boxes before saving
        self.format_date()
        self.format_price()

        print(f"Creating Appointment for Client ID {self.client_id}: {date}, {type}, {treatment}, {price}, {treatment_notes}")

        try:
            with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO appointments (client_id, date, type, treatment, price, photos_taken, treatment_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (self.client_id, date, type, treatment, price, "No", treatment_notes if treatment_notes else "<No notes added>"))
                conn.commit()

            print(f"New appointment created for Client ID {self.client_id} on {date} at {type}.")

            # Refresh the appointments list & close the window
            self.load_client_appointments(self.client_id)
            self.appointment_window.destroy()

        except Exception as e:
            print(f"Error saving new appointment: {e}")


    def update_appointment(self):
        """Open a dialog to update an existing appointment."""
        selected_item = self.appointments_table.selection()
        if not selected_item:
            print("No appointment selected for update.")
            return

        # Fetch appointment data from TreeView
        item_data = self.appointments_table.item(selected_item[0], "values")
        appointment_id = self.get_selected_appointment_id(selected_item[0])

        if not appointment_id:
            print("Unable to determine appointment ID.")
            return

        with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT treatment_notes FROM appointments WHERE id = ?", (appointment_id,))
            treatment_notes_result = cursor.fetchone()
            treatment_notes = treatment_notes_result[0] if treatment_notes_result else ""

        date, type, treatment, price, photos_taken = item_data

        # CREATE POP-UP WINDOW --> Update Appointment
        self.appointment_window = ctk.CTkToplevel()
        self.appointment_window.title("Update Appointment")
        self.appointment_window.geometry("500x400")
        self.appointment_window.resizable(True, True)

        # FORCE POP-UP AS TOP WINDOW & DISABLE MAIN WINDOW
        self.appointment_window.transient(self.main_app)  # Make it child of main app
        self.appointment_window.grab_set()  # Disable main window interaction
        self.appointment_window.focus_force()  # Force focus on the popup

        # Ensure proper window stretching
        self.appointment_window.grid_rowconfigure((0, 2), weight=1)
        self.appointment_window.grid_rowconfigure(1, weight=1)
        self.appointment_window.grid_columnconfigure(0, weight=1)

        # Row 0 [appt_window]: Create pop-up main frame
        self.pop_main_frame = ctk.CTkFrame(self.appointment_window)
        self.pop_main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ###########################################################
        ### ---------- POP_MAIN_FRAME CONTENTS BELOW ---------- ###
        ###########################################################

        # Ensure `pop_main_frame` expands properly
        self.pop_main_frame.columnconfigure((0, 2, 4), weight=1)  # Entry weights
        self.pop_main_frame.columnconfigure((1, 3, 5), weight=1)  # Label weights
        self.pop_main_frame.rowconfigure((0, 1, 2), weight=1)

        # Row 0 [pop_main_frame]: DATE Label/Entry
        ctk.CTkLabel(self.pop_main_frame, text="Date", anchor="w", width=70, fg_color="#dbdbdb").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.date_entry = ctk.CTkEntry(self.pop_main_frame, placeholder_text="MM/DD/YYYY")
        self.date_entry.insert(0, date)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.date_entry.bind("<Return>", lambda event: (self.format_date(), self.focus_next_widget(event)))
        self.date_entry.bind("<FocusOut>", lambda event: self.format_date())

        # Row 0 [pop_main_frame]: TYPE Label/Entry
        ctk.CTkLabel(self.pop_main_frame, text="Type", anchor="w", width=70).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.type_entry = ctk.CTkEntry(self.pop_main_frame, placeholder_text="Facial, etc.")
        self.type_entry.insert(0, type)
        self.type_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.type_entry.bind("<Return>", lambda event: self.focus_next_widget(event))
        self.type_entry.bind("<FocusOut>")

        # Row 0 [pop_main_frame]: PRICE Label/Entry
        ctk.CTkLabel(self.pop_main_frame, text="Price", anchor="w", width=70).grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.price_entry = ctk.CTkEntry(self.pop_main_frame, placeholder_text="$0.00")
        self.price_entry.insert(0, price)
        self.price_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        self.price_entry.bind("<Return>", lambda event: (self.format_price(), self.focus_next_widget(event)))
        self.price_entry.bind("<FocusOut>", lambda event: self.format_price())

        # Row 1 [pop_main_frame]: TREATMENT Label/Entry
        ctk.CTkLabel(self.pop_main_frame, text="Treatment", anchor="w", width=102).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.treatment_entry = ctk.CTkEntry(self.pop_main_frame, placeholder_text="Treatment Name")
        self.treatment_entry.insert(0, treatment)
        self.treatment_entry.grid(row=1, column=1, columnspan=5, padx=5, pady=5, sticky="ew")

        ###########################################################
        ### ---------- POP_MAIN_FRAME CONTENTS ABOVE ---------- ###
        ###########################################################

        # Row 1 [appt_window]: Create NOTES Frame
        self.notes_frame = ctk.CTkFrame(self.appointment_window, fg_color="#dbdbdb")
        self.notes_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

       # Ensure the notes frame stretches properly
        self.notes_frame.grid_rowconfigure(0, weight=1)
        self.notes_frame.grid_columnconfigure(0, weight=1)

        # Row 1 [notes_frame]: NOTES Label/Textbox
        self.notes_label = ctk.CTkLabel(self.notes_frame, text="Notes", fg_color="transparent").grid(row=0, column=0, sticky="w", padx=5)
        self.current_notes_textbox = ctk.CTkTextbox(self.notes_frame, corner_radius=0, wrap="word", fg_color="#ebebeb")
        self.current_notes_textbox.insert("1.0", treatment_notes)
        self.current_notes_textbox.grid(row=1, column=0, sticky="nsew")

        # Row 2 [appt_window]: Save Button
        self.save_button = ctk.CTkButton(self.notes_frame, text="Update", command=lambda: self.save_updated_appointment(appointment_id))
        self.save_button.grid(row=2, column=0, pady=10)


    def save_updated_appointment(self, appointment_id):
        """Save the updated appointment details."""
        date = self.date_entry.get().strip()
        type = self.type_entry.get().strip()
        treatment = self.treatment_entry.get().strip()
        price = self.price_entry.get().strip()
        treatment_notes = self.current_notes_textbox.get("1.0", "end").strip()

        # Validation check for required fields
        missing_fields = []
        if not date:
            missing_fields.append("- Date")
        if not treatment:
            missing_fields.append("- Treatment Name")
        if not price:
            missing_fields.append("- Price")

        if missing_fields:
            # Show warning message and return
            messagebox.showwarning("Missing Fields", f"Please fill out the following required fields:\n\n{chr(10).join(missing_fields)}")
            return

        # Apply formatting to all fields before saving
        self.format_date()
        self.format_price()

        print(f"Updating Appointment ID {appointment_id}: {date}, {type}, {treatment}, {price}, {treatment_notes}")

        try:
            with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE appointments 
                    SET date = ?, type = ?, treatment = ?, price = ?, treatment_notes = ?
                    WHERE id = ?
                """, (date, type, treatment, price, treatment_notes if treatment_notes else "<No notes added>", appointment_id))
                conn.commit()
                print(f"Appointment {appointment_id} updated successfully.")

            # Refresh the appointment list and close the window
            self.load_client_appointments(self.client_id)
            self.appointment_window.destroy()

        except Exception as e:
            print(f"Database update failed: {e}")

        # Update photos table to sync with the edited appointment
        try:
            with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE photos
                    SET appt_date = ?, type = ?
                    WHERE appointment_id = ?
                """, (date, type, appointment_id))
                conn.commit()
                print(f"Synced photos with updated appointment {appointment_id}")

            self.main_app.tabs["Photos"].refresh_photos_list(self.client_id)

        except Exception as e:
            print(f"Failed to update photos for appointment {appointment_id}: {e}")


    def get_selected_appointment_id(self, treeview_item):
        """Retrieve the appointment ID based on the TreeView selection."""
        try:
            return int(treeview_item)
        except Exception as e:
            print(f"Error retrieving appointment ID: {e}")
            return None


    def get_treatment_notes(self, appointment_id):
        """Fetch treatment notes for an appointment."""
        try:
            with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT treatment_notes 
                    FROM appointments 
                    WHERE id = ?
                """, (appointment_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
        except Exception as e:
            print(f"Failed to fetch treatment notes for appointment {appointment_id}: {e}")
            return ""


    def format_date(self):
        """Format the date entry to MM/DD/YYYY upon hitting Enter or leaving the field."""
        raw_date = self.date_entry.get().strip()

        if not raw_date:  # Keep placeholder if empty
            self.date_entry.delete(0, "end")
            return

        # Remove non-numeric characters except slashes, dashes, and dots
        cleaned_date = re.sub(r"[^0-9/.-]", "", raw_date)

        # Prevent re-formatting if already in correct format
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", cleaned_date):  
            return  # Exit early if already MM/DD/YYYY

        formatted_date = None  # Initialize

        try:
            # Convert formats like 12101992 → 12/10/1992
            if len(re.sub(r"\D", "", cleaned_date)) == 8:
                formatted_date = f"{cleaned_date[:2]}/{cleaned_date[2:4]}/{cleaned_date[4:]}"
            
            else:
                # Attempt to parse multiple formats
                for fmt in ["%m-%d-%Y", "%m.%d.%Y", "%m/%d/%Y"]:
                    try:
                        parsed_date = datetime.strptime(cleaned_date, fmt)
                        formatted_date = parsed_date.strftime("%m/%d/%Y")
                        break  # Exit loop on success
                    except ValueError:
                        formatted_date = None  # Keep None if no format matches

            if not formatted_date:
                raise ValueError("Invalid date format")

        except ValueError:
            print("⚠ Invalid date entered. Resetting to placeholder.")
            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, raw_date)  # Reset to prior date
            return

        # Insert the correctly formatted date
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, formatted_date)
        print(f"Formatted Date: {formatted_date}")


    def format_price(self, event=None):
        """Format the price entry to '$X.XX' upon hitting Enter or leaving the field."""
        raw_price = self.price_entry.get().strip()

        if not raw_price:  # Keep placeholder if empty
            self.price_entry.delete(0, "end")
            self.price_entry.insert(0, "$0.00")  # Default placeholder
            return

        # Prevent re-formatting if already formatted correctly
        if hasattr(self, "last_formatted_price") and self.last_formatted_price == raw_price:
            return

        # Extract numeric values (keep digits and decimal points)
        cleaned_price = re.sub(r"[^\d.]", "", raw_price)  # Remove non-numeric/non-decimal chars

        try:
            # Convert to float and format as '$ X.XX'
            formatted_price = f"${float(cleaned_price):.2f}"
        except ValueError:
            print("⚠ Invalid price entered. Resetting to placeholder.")
            self.price_entry.delete(0, "end")
            self.price_entry.insert(0, "$0.00")  # Reset to placeholder
            return

        # Store the formatted price to prevent redundant re-formatting
        self.last_formatted_price = formatted_price  

        # Insert the correctly formatted price
        self.price_entry.delete(0, "end")
        self.price_entry.insert(0, formatted_price)
        print(f"Formatted Price: {formatted_price}")


    def focus_next_widget(self, event):
        """Move focus to the next widget when pressing Enter."""
        event.widget.tk_focusNext().focus()
        return "break"  # Prevents default behavior (e.g., inserting a newline in text fields)


    def on_double_click_edit_appointment(self, event):
        """Open the Edit Appointment window when an appointment is double-clicked."""
        
        selected_item = self.appointments_table.selection()
        
        if not selected_item:
            print("⚠ No appointment selected for editing.")
            return

        print("Double-click detected. Opening Edit Window...")

        # Call `update_appointment()` to open the edit window
        self.update_appointment()


    def delete_appointment(self, event=None):
        """Delete the selected appointment from the database after user confirmation."""
        selected_item = self.appointments_table.selection()

        if not selected_item:
            print("No appointment selected for deletion.")
            return

        # Fetch appointment ID
        appointment_id = self.get_selected_appointment_id(selected_item[0])

        if not appointment_id:
            print("Unable to determine appointment ID. Deletion aborted.")
            return

        # Step 3: Create Confirmation Pop-up
        confirmation = ctk.CTkToplevel()
        confirmation.title("Confirm Deletion")
        confirmation.geometry("350x170")
        confirmation.resizable(False, False)
        
        # Make pop-up **always on top** and disable main window until closed
        confirmation.transient(self.main_app)  # Link to main app window
        confirmation.grab_set()  # Prevent interactions with main app until pop-up is closed
        confirmation.focus_force()  # Immediately focus the pop-up window

        # Main frame
        main_frame = ctk.CTkFrame(confirmation)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Confirmation Message
        ctk.CTkLabel(
            main_frame, 
            text="Are you sure you want to permanently delete this appointment?\n\nAll associated photos will also be removed.",
            font=("Helvetica", 14), wraplength=300
        ).pack(pady=(25, 10))

        # Buttons Frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=10)

        # Cancel Button (Closes Pop-up)
        ctk.CTkButton(button_frame, text="Cancel", command=confirmation.destroy).pack(side="left", padx=5)

        # Delete Button (Executes Deletion)
        ctk.CTkButton(
            button_frame, text="Delete", fg_color="#FF4444", hover_color="#CC0000",
            command=lambda: self._execute_delete_appointment(appointment_id, confirmation)
        ).pack(side="right", padx=5)


    def _execute_delete_appointment(self, appointment_id, confirmation_window):
        """Executes appointment deletion and closes the confirmation pop-up."""
        try:
            # --- Fetch and delete photo files associated with this appointment ---
            with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT file_path FROM photos WHERE appointment_id = ?", (appointment_id,))
                photo_rows = cursor.fetchall()

            folders_to_check = set()

            for (file_path,) in photo_rows:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"🗑️ Deleted photo file: {file_path}")

                        # Track the folder path for cleanup check
                        folder_path = os.path.dirname(file_path)
                        folders_to_check.add(folder_path)

                    except Exception as e:
                        print(f"Failed to delete file {file_path}: {e}")
                else:
                    print(f"File not found, skipping: {file_path}")

            # --- Attempt to delete now-empty folders ---
            for folder in folders_to_check:
                try:
                    if os.path.exists(folder) and not os.listdir(folder):  # folder exists and is empty
                        os.rmdir(folder)
                        print(f"Deleted empty folder: {folder}")
                except Exception as e:
                    print(f"Failed to delete folder {folder}: {e}")

            # --- Delete from database ---
            with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM photos WHERE appointment_id = ?", (appointment_id,))
                print(f"Deleted {len(photo_rows)} photo record(s) from database.")

                cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
                conn.commit()
                print(f"Appointment {appointment_id} deleted successfully.")

            # --- Refresh UI ---
            self.load_client_appointments(self.client_id)
            if "Photos" in self.main_app.tabs:
                self.main_app.tabs["Photos"].refresh_photos_list(self.client_id)

        except Exception as e:
            print(f"Error deleting appointment: {e}")

        finally:
            confirmation_window.destroy()


    def add_photos(self):
        selected_item = self.appointments_table.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an appointment first.")
            return

        # Get appointment details from Treeview
        appointment_data = self.appointments_table.item(selected_item[0], "values")
        appointment_id = self.get_selected_appointment_id(selected_item[0])  
        print(f"Selected Appointment ID: {appointment_id}")  # Debugging print
        if not appointment_data:
            messagebox.showerror("Error", "Could not retrieve appointment data.")
            return

        # Fetch values/init variables
        appt_date = appointment_data[0]  # Fetch appointment date (MM/DD/YYYY format)
        type = appointment_data[1]  # Fetch type name

        # Fetch full name of client using client id
        try:
            with sqlite3.connect(self.main_app.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT full_name FROM clients WHERE id = ?", (self.client_id,))
                result = cursor.fetchone()
                if not result:
                    messagebox.showerror("Error", "Failed to retrieve client's full name from database.")
                    return
                client_name = result[0]
                print(f"Retrieved Client: {client_name} (ID: {self.client_id}) | Appointment Date: {appt_date} (ID: {appointment_id})")
        except Exception as e:
            print(f"Database error while fetching client name: {e}")
            messagebox.showerror("Error", "An error occurred while accessing the database.")
            return

        # Launch popup and pass necessary info
        popup = PhotoUploadPopup(
            parent=self.main_app,
            client_id=self.client_id,
            appointment_id=appointment_id,
            appointment_date=appt_date,
            client_name=client_name,
            appt_type=type,
            main_app=self.main_app,
        )
        popup.grab_set()


    def update_alternating_colors(self):
        """Reassign even/odd row tags based on visual order."""
        for index, item in enumerate(self.appointments_table.get_children()):
            tag = "even" if index % 2 == 0 else "odd"
            self.appointments_table.item(item, tags=(tag,))