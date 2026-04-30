import os
from fpdf import FPDF
from PIL import Image
from config_manager import ConfigManager

class MaterialConfirmationPDF(FPDF):
    def __init__(self, client_info, assets_path):
        super().__init__(format="letter")
        self.client_info = client_info
        self.assets_path = assets_path
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        if self.page_no() == 1:
            return

        header_img = os.path.join(self.assets_path, "New Header 2025.png")
        if os.path.exists(header_img):
            self.image(header_img, x=0, y=0, w=215.9)
            self.set_y(40) 
        else:
            self.set_font("helvetica", "B", 16)
            self.cell(0, 10, "PKB - Payless Kitchen & Bath", border=False, ln=True, align="C")
            self.set_font("helvetica", "I", 10)
            self.cell(0, 5, "Material Confirmation Document", border=False, ln=True, align="C")
            self.ln(5)
        
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
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no() - 1} - Please review all materials carefully before final approval.", align="C")

class PDFGenerator:
    def __init__(self, base_path="database", output_path="output"):
        self.assets_path = os.path.join(base_path, "assets")
        self.output_path = output_path
        self.temp_path = "temp"
        
        os.makedirs(self.output_path, exist_ok=True)
        os.makedirs(self.temp_path, exist_ok=True)

    def optimize_image(self, image_filename):
        original_path = os.path.join(self.assets_path, image_filename)
        if not os.path.exists(original_path):
            return None
        
        temp_file_path = os.path.join(self.temp_path, f"opt_{image_filename}")
        
        try:
            with Image.open(original_path) as img:
                if img.mode != 'RGB': img = img.convert('RGB')
                max_width = 800
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int((float(img.height) * float(ratio)))
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                img.save(temp_file_path, "JPEG", quality=75)
            return temp_file_path
        except Exception as e:
            print(f"  [!] Error optimizing image {image_filename}: {e}")
            return None

    def optimize_custom_image(self, absolute_path):
        if not os.path.exists(absolute_path):
            return None
        
        filename = os.path.basename(absolute_path)
        temp_file_path = os.path.join(self.temp_path, f"opt_custom_{filename}")
        
        try:
            with Image.open(absolute_path) as img:
                if img.mode != 'RGB': img = img.convert('RGB')
                max_width = 1200 
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int((float(img.height) * float(ratio)))
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                img.save(temp_file_path, "JPEG", quality=85)
            return temp_file_path
        except Exception as e:
            print(f"  [!] Error optimizing custom image: {e}")
            return None

    def create_pdf(self, payload):
        client_info = payload.get("client_info", {})
        products = payload.get("products", [])
        custom_pages = payload.get("custom_pages", [])
        
        pdf = MaterialConfirmationPDF(client_info, self.assets_path)
        pdf.add_page()
        
        # --- COVER PAGE ---
        cover_filename = ConfigManager.get("cover_image_filename")
        if not cover_filename:
            cover_filename = "Bath Document Cover Page.png"
            
        cover_img = os.path.join(self.assets_path, cover_filename)
        if os.path.exists(cover_img):
            pdf.image(cover_img, x=0, y=0, w=215.9)
            pdf.set_y(150) 
            
            pdf.set_font("helvetica", "I", 14)
            pdf.set_text_color(142, 142, 142) 
            pdf.cell(0, 8, "Prepared for:", ln=True, align="C")
            
            client_name_display = client_info.get("name", "Valued Client")
            pdf.set_font("helvetica", "B", 34)
            pdf.set_text_color(21, 62, 131) 
            pdf.cell(0, 14, client_name_display, ln=True, align="C")
            
            pdf.ln(4)
            
            pdf.set_font("helvetica", "I", 14)
            pdf.set_text_color(142, 142, 142)
            pdf.cell(0, 6, "Project:", ln=True, align="C")
            
            project_name_display = client_info.get('project', 'Remodel Project')
            pdf.set_font("helvetica", "B", 22)
            pdf.set_text_color(1, 161, 219)
            pdf.cell(0, 10, project_name_display, ln=True, align="C")
            
            pdf.add_page()
        
        pdf.set_text_color(0, 0, 0)
        
        # --- GROUP BY ROOM ---
        from collections import defaultdict
        rooms = defaultdict(list)
        for item in products:
            if "printable" not in item or not item["printable"]:
                continue
            rooms[item.get("room", "Misc")].append(item)
            
        # --- PRODUCTS ---
        for room_name, room_products in rooms.items():
            if not room_products:
                continue
                
            # Print Room Header
            pdf.ln(5)
            pdf.set_font("helvetica", "B", 16)
            pdf.set_text_color(1, 161, 219)
            pdf.cell(0, 10, room_name.upper(), ln=True, align="L")
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
            pdf.ln(5)
            
            for item in room_products:
                printable = item.get("printable", {})
                target_w = 90
                target_h = 0
                opt_image_path = None
                
                image_file = printable.get("image_file")
                if image_file:
                    opt_image_path = self.optimize_image(image_file)
                    if opt_image_path:
                        with Image.open(opt_image_path) as img:
                            img_w, img_h = img.size
                        ratio = img_h / img_w
                        target_h = target_w * ratio
                        
                        if target_h > 100:
                            target_h = 100
                            target_w = target_h / ratio
                
                block_height = 8 + 6 + 15  
                if printable.get("dimensions", {}):
                    block_height += 6
                if opt_image_path:
                    block_height += target_h + 5
                else:
                    block_height += 10
                block_height += 10 
                
                if pdf.get_y() + block_height > 260:
                    pdf.add_page()
                
                pdf.set_font("helvetica", "B", 12)
                pdf.set_text_color(0, 51, 102)
                qty = item.get("quantity", item.get("qty", 1))
                qty_str = f" (Qty: {qty})" if qty > 1 else ""
                
                title = printable.get('description', 'Item Description')
                pdf.multi_cell(0, 8, f"{title}{qty_str}")
                
                pdf.set_font("helvetica", "", 10)
                pdf.set_text_color(0, 0, 0)
                
                specs = []
                if printable.get("finish"):
                    specs.append(f"Finish: {printable.get('finish')}")
                    
                if specs:
                    pdf.cell(0, 6, " | ".join(specs), ln=True)
                
                dims = printable.get("dimensions", {})
                if dims:
                    dim_string = " | ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in dims.items()])
                    pdf.cell(0, 6, f"Dimensions: {dim_string}", ln=True)
                
                if opt_image_path:
                    pdf.image(opt_image_path, w=target_w, h=target_h)
                    pdf.ln(5)
                else:
                    pdf.set_font("helvetica", "B", 10)
                    pdf.set_text_color(255, 0, 0)
                    pdf.cell(0, 10, "[ Image missing from database assets ]", ln=True)
                    pdf.set_text_color(0, 0, 0)
                
                pdf.ln(3)
                pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
                pdf.ln(3) 
                
        # --- CUSTOM PAGES ---
        for page_data in custom_pages:
            # Handle backwards compatibility if it's just a string path
            if isinstance(page_data, str):
                img_path = page_data
                title = ""
            else:
                img_path = page_data.get("path", "")
                title = page_data.get("title", "")

            if os.path.exists(img_path):
                pdf.add_page()
                
                # Print Title if provided
                if title:
                    pdf.set_font("helvetica", "B", 16)
                    pdf.set_text_color(0, 51, 102)
                    pdf.cell(0, 10, title, ln=True, align="C")
                    pdf.ln(5)
                    
                opt_path = self.optimize_custom_image(img_path)
                if opt_path:
                    pdf.image(opt_path, x=13, y=pdf.get_y(), w=190)
        
        # --- EXPORT ---
        client_name_safe = client_info.get("name", "Client").replace(" ", "_")
        output_filename = os.path.join(self.output_path, f"{client_name_safe}_Confirmation.pdf")
        pdf.output(output_filename)
        
        print(f"✅ PDF successfully exported to: {output_filename}")
        return output_filename