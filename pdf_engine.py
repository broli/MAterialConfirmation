import os
from fpdf import FPDF
from PIL import Image

class MaterialConfirmationPDF(FPDF):
    def __init__(self, client_info, assets_path):
        # Force 'letter' format to match the marketing design
        super().__init__(format="letter")
        self.client_info = client_info
        self.assets_path = assets_path
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # Skip the standard header on the cover page
        if self.page_no() == 1:
            return

        # Marketing header image path
        header_img = os.path.join(self.assets_path, "New Header 2025.png")
        
        if os.path.exists(header_img):
            # Full bleed header
            self.image(header_img, x=0, y=0, w=215.9)
            self.set_y(40) 
        else:
            # Fallback text
            self.set_font("helvetica", "B", 16)
            self.cell(0, 10, "PKB - Payless Kitchen & Bath", border=False, ln=True, align="C")
            self.set_font("helvetica", "I", 10)
            self.cell(0, 5, "Material Confirmation Document", border=False, ln=True, align="C")
            self.ln(5)
        
        # Client Information Block
        self.set_font("helvetica", "B", 10)
        client_name = self.client_info.get("name", "Valued Client")
        project_name = self.client_info.get("project", "Remodel Project")
        date = self.client_info.get("date", "")
        
        header_text = f"Client: {client_name} | Project: {project_name}"
        if date:
            header_text += f" | Date: {date}"
            
        self.cell(0, 6, header_text, border="B", ln=True, align="L")
        self.ln(5)

    def footer(self):
        # Skip the footer on the cover page
        if self.page_no() == 1:
            return

        # Footer with adjusted page numbers (content starts as Page 1)
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no() - 1} - Please review all materials carefully before final approval.", align="C")

class PDFGenerator:
    def __init__(self, base_path="database"):
        self.assets_path = os.path.join(base_path, "assets")
        self.output_path = "output"
        self.temp_path = "temp"
        
        # Ensure required directories exist
        os.makedirs(self.output_path, exist_ok=True)
        os.makedirs(self.temp_path, exist_ok=True)

    def optimize_image(self, image_filename):
        """Uses Pillow to resize and compress the image to keep PDF size small."""
        original_path = os.path.join(self.assets_path, image_filename)
        if not os.path.exists(original_path):
            return None
        
        temp_file_path = os.path.join(self.temp_path, f"opt_{image_filename}")
        
        try:
            with Image.open(original_path) as img:
                # Convert to RGB to prevent issues with PNG transparency in PDFs
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if the image is wider than 800px
                max_width = 800
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int((float(img.height) * float(ratio)))
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Save as JPEG with compression
                img.save(temp_file_path, "JPEG", quality=75)
            return temp_file_path
        except Exception as e:
            print(f"  [!] Error optimizing image {image_filename}: {e}")
            return None

    def create_pdf(self, payload):
        """Builds the actual PDF document using the provided payload."""
        client_info = payload.get("client_info", {})
        products = payload.get("products", [])
        
        # Pass self.assets_path so the header can find the marketing image
        pdf = MaterialConfirmationPDF(client_info, self.assets_path)
        
        pdf.add_page()
        
        # --- NEW COVER PAGE LOGIC ---
        cover_img = os.path.join(self.assets_path, "Bath Document Cover Page.png")
        if os.path.exists(cover_img):
            # Stamp the cover image full bleed
            pdf.image(cover_img, x=0, y=0, w=215.9)
            
            # Adjusted Y value to place the text higher on the page
            pdf.set_y(170) 
            
            # 1. "Prepared for:" Label (Gray #8E8E8E)
            pdf.set_font("helvetica", "I", 14)
            pdf.set_text_color(142, 142, 142) 
            pdf.cell(0, 8, "Prepared for:", ln=True, align="C")
            
            # 2. Client Name (Dark Blue #153E83, Much Bigger)
            client_name_display = client_info.get("name", "Valued Client")
            pdf.set_font("helvetica", "B", 34)
            pdf.set_text_color(21, 62, 131) 
            pdf.cell(0, 14, client_name_display, ln=True, align="C")
            
            pdf.ln(4) # Small visual gap
            
            # 3. "Project:" Label (Gray #8E8E8E)
            pdf.set_font("helvetica", "I", 14)
            pdf.set_text_color(142, 142, 142)
            pdf.cell(0, 6, "Project:", ln=True, align="C")
            
            # 4. Project Name (Light Blue #01A1DB, Medium Size)
            project_name_display = client_info.get('project', 'Remodel Project')
            pdf.set_font("helvetica", "B", 22)
            pdf.set_text_color(1, 161, 219)
            pdf.cell(0, 10, project_name_display, ln=True, align="C")
            
            # Start a new page for the actual products
            pdf.add_page()
        # ----------------------------
        
        # Reset text color to black before printing items
        pdf.set_text_color(0, 0, 0)
        
        for item in products:
            # unbreakable() keeps the product details and its photo glued together
            with pdf.unbreakable():
                # --- Product Title ---
                pdf.set_font("helvetica", "B", 12)
                pdf.set_text_color(0, 51, 102) # Dark Blue
                pdf.cell(0, 8, f"{item.get('brand', '')} - {item.get('model', '')}", ln=True)
                
                # --- Product Specs ---
                pdf.set_font("helvetica", "", 10)
                pdf.set_text_color(0, 0, 0) # Black reset
                pdf.cell(0, 6, f"Type: {item.get('type', '')} | Finish: {item.get('finish', '')}", ln=True)
                
                # --- Dynamic Dimensions ---
                dims = item.get("dimensions", {})
                if dims:
                    dim_string = " | ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in dims.items()])
                    pdf.cell(0, 6, f"Dimensions: {dim_string}", ln=True)
                
                # --- Description ---
                pdf.set_font("helvetica", "I", 9)
                pdf.multi_cell(0, 5, item.get('description', ''))
                pdf.ln(2)
                
                # --- Image Processing ---
                image_file = item.get("image_file")
                if image_file:
                    opt_image_path = self.optimize_image(image_file)
                    if opt_image_path:
                        # width 90mm keeps it neat, height auto-scales
                        pdf.image(opt_image_path, w=90)
                        pdf.ln(5)
                    else:
                        pdf.set_font("helvetica", "B", 10)
                        pdf.set_text_color(255, 0, 0)
                        pdf.cell(0, 10, "[ Image missing from database assets ]", ln=True)
                        pdf.set_text_color(0, 0, 0)
                
                # --- Visual Separator ---
                # FIX: Replaced line() with a zero-height cell that has a bottom border to avoid get_y() errors
                pdf.ln(5)
                pdf.cell(0, 0, "", border="B", ln=True)
                pdf.ln(10)
        
        # --- Export ---
        client_name_safe = client_info.get("name", "Client").replace(" ", "_")
        output_filename = os.path.join(self.output_path, f"{client_name_safe}_Confirmation.pdf")
        pdf.output(output_filename)
        
        print(f"✅ PDF successfully exported to: {output_filename}")
        return output_filename