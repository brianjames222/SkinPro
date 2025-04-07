import customtkinter as ctk
from customtkinter import CTkImage
from tkinter import ttk
from PIL import Image, ImageTk
from class_elements.treeview_styling_light import style_treeview_light
import os
from pdf2image import convert_from_path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import textwrap
from CTkMessagebox import CTkMessagebox
from prescriptions.pdf_generators.pdf_2col import Pdf2ColGenerator
from prescriptions.pdf_generators.pdf_3col import Pdf3ColGenerator
from prescriptions.pdf_generators.pdf_4col import Pdf4ColGenerator
from prescriptions.pdf_generators.prescription_entry_popup import PrescriptionEntryPopup


class PrescriptionsPage:
    def __init__(self, parent, conn, main_app):
        self.conn = conn
        self.cursor = conn.cursor() if conn else None
        self.main_app = main_app
        self.appointment_id = None
        self.current_prescription_id = None
        self.pdf_2col = Pdf2ColGenerator()
        self.pdf_3col = Pdf3ColGenerator()
        self.pdf_4col = Pdf4ColGenerator()

        self.prescription_paths = {}  # {iid: filepath}

        # Main container
        main_frame = ctk.CTkFrame(parent)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Configure Grid Layout
        main_frame.columnconfigure(0, weight=1)  # Treeview
        main_frame.columnconfigure(1, weight=4)  # Prescription display
        main_frame.columnconfigure(2, weight=0)  # Buttons
        main_frame.rowconfigure(0, weight=1)

        # Treeview Frame (Past Prescriptions)
        treeview_frame = ctk.CTkFrame(main_frame)
        treeview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Apply treeview styling
        style_treeview_light("Prescriptions.Treeview")

        # Grid layout in treeview_frame
        treeview_frame.rowconfigure(0, weight=1)
        treeview_frame.columnconfigure(0, weight=1)

        # Style and Treeview
        self.prescription_list = ttk.Treeview(treeview_frame, selectmode="browse", show="headings", style="Prescriptions.Treeview")
        self.prescription_list["columns"] = ("date", "template")
        self.prescription_list.heading("date", text="Date")
        self.prescription_list.heading("template", text="Template")
        self.prescription_list.column("date", width=90, anchor="center")
        self.prescription_list.column("template", width=90, anchor="center")
        self.prescription_list.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for Treeview
        scrollbar = ttk.Scrollbar(treeview_frame, orient="vertical", command=self.prescription_list.yview, style="Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.prescription_list.configure(yscrollcommand=scrollbar.set)

        # === Prescription Display Area (Editable or PDF Preview Placeholder) ===
        display_frame = ctk.CTkFrame(main_frame, fg_color="#563A9C")
        display_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 5))

        ctk.CTkLabel(display_frame, text="Current Prescription", font=("Helvetica", 16, "bold"),
                    fg_color="transparent", text_color="#ebebeb").pack()

        # === Scrollable Frame for PDF Preview ===
        self.scroll_canvas = ctk.CTkCanvas(display_frame, highlightthickness=0)
        self.scroll_canvas.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Hidden Scrollbar (not placed in layout)
        scrollbar = ctk.CTkScrollbar(display_frame, orientation="vertical", command=self.scroll_canvas.yview)
        scrollbar.configure(border_spacing=0)

        # Still connect canvas to scrollbar for yview tracking
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)

        # === Internal Frame inside Canvas ===
        self.preview_inner_frame = ctk.CTkFrame(self.scroll_canvas)
        self.scroll_window = self.scroll_canvas.create_window((0, 0), window=self.preview_inner_frame, anchor="nw")

        # === Scroll Region & Mouse Events ===
        self.preview_inner_frame.bind("<Configure>", self._update_scroll_region)
        self._bind_mousewheel_events()

        # Button Column on the Right
        button_column = ctk.CTkFrame(main_frame)
        button_column.grid(row=0, column=2, sticky="ns", padx=(5, 0))

        # Buttons stacked vertically
        button_specs = [
            ("New Prescription", self.create_prescription),
            ("Edit Prescription", self.edit_prescription),
            ("Delete Prescription", self.delete_prescription),
            ("Preview PDF", self.preview_prescription),
            ("Print Prescription", self.print_prescription),
            ("Set Alert", self.set_alert)
        ]

        for text, command in button_specs:
            ctk.CTkButton(button_column, text=text, width=160, command=command).pack(fill="x", pady=(0, 10))


    def create_prescription(self):
        client_id = getattr(self.main_app.profile_card, "client_id", None)
        if not client_id:
            ctk.CTkLabel(self.main_app, text="No client selected.", text_color="red").pack(pady=10)
            return

        cursor = self.conn.cursor()
        PrescriptionEntryPopup(self.main_app, self.handle_prescription_submission, client_id, cursor)


    def handle_prescription_submission(self, pdf_path, data):
        # Grab current date as string
        start_date = datetime.today().strftime("%m/%d/%Y")
        num_columns = sum(1 for key in data if key.startswith("Col") and "_Header" in key)

        # Create Treeview item
        iid = self.prescription_list.insert(
            "", "end",
            values=(start_date, f"{num_columns} Column{'s' if num_columns > 1 else ''}")
        )

        # Track the PDF path
        self.prescription_paths[iid] = pdf_path

        # Auto-select and preview it
        self.prescription_list.selection_set(iid)
        self.render_pdf_to_preview(pdf_path)


    def add_prescription_to_list(self, date, template, path):
        iid = self.prescription_list.insert("", "end", values=(date, template))
        self.prescription_paths[iid] = path


    def edit_prescription(self):
        print("✏️ Edit current prescription")


    def delete_prescription(self):
        selected = self.prescription_list.selection()
        if not selected:
            print("❌ No prescription selected for deletion.")
            return

        iid = selected[0]
        pdf_path = self.prescription_paths.get(iid)

        # Optional: confirm deletion
        confirm = CTkMessagebox(title="Delete?", message="Are you sure you want to delete this prescription?", icon="warning", option_1="Yes", option_2="Cancel")
        if confirm.get() != "Yes":
            return

        try:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
                print(f"🗑️ Deleted file: {pdf_path}")

            # Delete from database
            self.cursor.execute("DELETE FROM prescriptions WHERE file_path = ?", (pdf_path,))
            self.conn.commit()

            # Remove from Treeview and internal dict
            self.prescription_list.delete(iid)
            del self.prescription_paths[iid]

        except Exception as e:
            print(f"❌ Failed to delete prescription: {e}")


    def preview_prescription(self):
        selected = self.prescription_list.selection()
        if not selected:
            print("❌ No prescription selected.")
            return

        iid = selected[0]
        pdf_path = self.prescription_paths.get(iid)

        if not pdf_path or not os.path.exists(pdf_path):
            print("❌ PDF file not found for preview.")
            return

        # Open popout window
        self.open_pdf_popup(pdf_path)

    def open_pdf_popup(self, pdf_path):
        popup = ctk.CTkToplevel()
        popup.title("Full Size PDF Preview")

        popup.geometry("850x1100")  # Or adjust to your desired full-size dimensions
        popup.configure(fg_color="#ebebeb")

        # Lock interaction to this window only
        popup.grab_set()

        try:
            pages = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)

            if pages:
                image = pages[0]
                image = image.resize((850, int(850 * 11 / 8.5)))  # Maintain letter ratio
                tk_image = ImageTk.PhotoImage(image)

                label = ctk.CTkLabel(popup, image=tk_image, text="")
                label.image = tk_image
                label.pack(padx=10, pady=10)
                print("✅ PDF displayed in popup window.")
            else:
                print("⚠️ No pages found in PDF.")

        except Exception as e:
            print(f"❌ Failed to load PDF for popup: {e}")


    def print_prescription(self):
        selected = self.prescription_list.selection()
        if not selected:
            print("❌ No prescription selected.")
            return

        iid = selected[0]
        pdf_path = self.prescription_paths.get(iid)

        if not pdf_path or not os.path.exists(pdf_path):
            print("❌ PDF file not found.")
            return

        try:
            # For Windows
            os.startfile(pdf_path, "print")
            print("🖨️ Sent to printer.")
        except Exception as e:
            print(f"❌ Failed to print: {e}")


    def set_alert(self):
        print("🔔 Set reminder alert")
  

    def render_pdf_to_preview(self, pdf_path):
        try:
            # Convert only the first page to an image
            pages = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)

            if pages:
                image = pages[0]

                # Scale image to width=464, keep aspect ratio (Letter ratio is ~1.294)
                display_width = 464
                aspect_ratio = image.height / image.width
                display_height = int(display_width * aspect_ratio)

                # Resize CTkImage
                ctk_image = CTkImage(light_image=image, size=(display_width, display_height))

                # Clear previous image
                for widget in self.preview_inner_frame.winfo_children():
                    widget.destroy()

                label = ctk.CTkLabel(self.preview_inner_frame, image=ctk_image, text="", fg_color="#ebebeb")
                label.image = ctk_image  # Keep a reference
                label.pack()

                print("✅ PDF rendered inside scrollable frame.")
            else:
                print("⚠️ No pages found in PDF.")
        except Exception as e:
            print(f"❌ Failed to render PDF: {e}")


    def on_prescription_select(self, event):
        selected = self.prescription_list.selection()
        if selected:
            iid = selected[0]
            path = self.prescription_paths.get(iid)
            if path and os.path.exists(path):
                self.render_pdf_to_preview(path)


    def _update_scroll_region(self, event):
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))


    def _on_mousewheel(self, event):
        self.scroll_canvas.yview_scroll(-1 * (event.delta // 120), "units")


    def _bind_mousewheel_events(self):
        self.scroll_canvas.bind("<Enter>", lambda e: self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.scroll_canvas.bind("<Leave>", lambda e: self.scroll_canvas.unbind_all("<MouseWheel>"))
