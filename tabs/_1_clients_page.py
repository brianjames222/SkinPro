from tkinter import ttk
import customtkinter as ctk
from PIL import Image
from class_elements.profile_card import ProfileCard


class ClientsPage:
    def __init__(self, parent, conn, main_app):
        self.parent = parent
        self.conn = conn
        self.main_app = main_app
        self.cursor = conn.cursor()

        # Add the profile display
        self.profile_display = ProfileCard(parent)

        # Frame for Search and Treeview
        main_frame = ctk.CTkFrame(parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame for Search Bar
        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        # Search Label
        search_label = ctk.CTkLabel(search_frame, text="Search by Name:", font=("Arial", 14))
        search_label.grid(row=0, column=0, sticky="w", padx=10)

        # Search Entry
        self.name_entry = ctk.CTkEntry(search_frame, width=300, placeholder_text="Enter client name", border_width=0)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=0)

        # Bind Enter key to search function
        self.name_entry.bind("<Return>", lambda event: self.search_client())

        # Add Client Button
        add_client_icon = ctk.CTkImage(light_image=Image.open("icons/add_client.png"), size=(24, 24))
        add_client_button = ctk.CTkButton(
            search_frame,
            image=add_client_icon,
            text="",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color="#444444",
            command=self.add_client_button_pressed
        )
        add_client_button.grid(row=0, column=2, padx=5)

        # Configure the columns in the search_frame
        search_frame.columnconfigure(1, weight=1)  # Make the entry box expand

        # Frame for Treeview and Scrollbar
        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True)

        # Treeview Widget
        columns = ("Name", "Gender", "Birthdate", "Phone #", "Email", "Address")
        self.client_list = ttk.Treeview(table_frame, columns=columns, show="headings")

        # Define column headers
        self.client_list.heading("Name", text="Name")
        self.client_list.heading("Gender", text="Gender")
        self.client_list.heading("Birthdate", text="Birthdate")
        self.client_list.heading("Phone #", text="Phone #")
        self.client_list.heading("Email", text="Email")
        self.client_list.heading("Address", text="Address")

        # Set initial column widths
        self.set_column_widths()

        # Pack the Treeview
        self.client_list.pack(side="left", fill="both", expand=True)

        # Add vertical scrollbar
        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.client_list.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.client_list.configure(yscrollcommand=scrollbar_y.set)

        # Load data from the database
        self.load_clients()

        # No Results label (initially hidden)
        self.no_results_label = ctk.CTkLabel(
            table_frame,
            text="",
            bg_color="#1E1E1E",
            font=("Arial", 24),
            text_color="white",
            anchor="center"
        )
        self.no_results_label.place(relx=0.5, rely=0.5, anchor="center")
        self.no_results_label.lower()  # Hide the label by lowering it below the Treeview

        # Bind the Treeview's parent to a resize event
        self.client_list.bind("<Configure>", lambda event: self.set_column_widths())

        # Bind "Control+Enter" to the button's functionality globally
        self.main_app.bind("<Control-Return>", lambda event: self.add_client_button_pressed())  # For Windows/Linux
        self.main_app.bind("<Command-Return>", lambda event: self.add_client_button_pressed())  # For macOS
        self.client_list.bind("<Double-1>", self.load_selected_client)
        self.client_list.bind("<Control-Return>", self.add_client_button_pressed)

        # Ensure focus is set to an interactive widget
        self.name_entry.focus_set()  # This will allow the shortcut to work when typing in the entry

    def set_column_widths(self):
        # Get the current width of the Treeview
        total_width = self.client_list.winfo_width()

        # Set column widths as percentages of the total width
        self.client_list.column("Name", width=int(total_width * 0.20), minwidth=150)
        self.client_list.column("Gender", width=int(total_width * 0.05), minwidth=55)
        self.client_list.column("Birthdate", width=int(total_width * 0.10), minwidth=80)
        self.client_list.column("Phone #", width=int(total_width * 0.15), minwidth=100)
        self.client_list.column("Email", width=int(total_width * 0.10), minwidth=200)
        self.client_list.column("Address", width=int(total_width * 0.40), minwidth=200)

    def load_clients(self):
        """Load all clients from the database and insert them into the Treeview."""
        self.client_list.delete(*self.client_list.get_children())  # Clear existing rows
        self.cursor.execute("SELECT full_name, gender, birthdate, phone, email, address1 || ', ' || address2 FROM clients")
        for row in self.cursor.fetchall():
            self.client_list.insert("", "end", values=row)

    def search_client(self):
        """Search for clients based on the name entered in the search box."""
        query = self.name_entry.get()
        if query:
            self.client_list.delete(*self.client_list.get_children())  # Clear existing rows
            self.cursor.execute("""
                SELECT full_name, gender, birthdate, phone, email, address1 || ', ' || address2 
                FROM clients 
                WHERE full_name LIKE ?
            """, (f"%{query}%",))
            results = self.cursor.fetchall()
            if results:
                for row in results:
                    self.client_list.insert("", "end", values=row)
                self.no_results_label.lower()  # Hide the "No Results" label
            else:
                # Show the "No Results" label and configure its text
                self.no_results_label.configure(
                    text=f"No results for '{query}'\n\nPress Ctrl + Enter to add."
                )
                self.no_results_label.lift()  # Bring the label to the front
        else:
            self.load_clients()  # Reload all clients if no search query is provided
            self.no_results_label.lower()  # Hide the "No Results" label

    def load_selected_client(self, event):
        """Load the selected client and update other tabs."""
        selected_item = self.client_list.selection()
        if not selected_item:
            return

        client_data = self.client_list.item(selected_item)["values"]
        if client_data:
            full_name = client_data[0]  # First column is full_name
            self.cursor.execute("SELECT id FROM clients WHERE full_name = ?", (full_name,))
            client_id = self.cursor.fetchone()
            if client_id:
                client_id = client_id[0]
                self.main_app.tabs["Info"].populate_client_info(client_id)
                self.main_app.tabs["Appointments"].load_client_appointments(client_id)

                # Switch to the Info tab
                self.main_app.switch_to_tab("Info")

    def add_client_button_pressed(self):
        """Switch to the Info Tab, clear data, and populate the full name."""
        full_name = self.name_entry.get()  # Get the name entered in the search field

        # Clear the Info and Appointments tabs
        self.main_app.tabs["Info"].clear_info()  # Clear all fields in the Info tab
        self.main_app.tabs["Appointments"].clear_appointments()  # Clear appointments data

        # Set the current client to a placeholder ID (-1 for new clients)
        self.main_app.current_client_id = -1

        # Populate the full name entry in the Info tab
        info_tab = self.main_app.tabs["Info"]
        info_tab.full_name_entry.insert(0, full_name)  # Insert the entered name

        # Switch to the Info tab
        self.main_app.switch_to_tab("Info")
