import os
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side

class ExcelRoutingEngine:
    def __init__(self, template_path="raw/2. Order form V7.xlsx", output_dir="output"):
        self.template_path = template_path
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_excel(self, verified_session_data):
        client_name = verified_session_data.get("client_name", "Unknown Client")
        project_po = verified_session_data.get("project_po", "Unknown PO")
        items = verified_session_data.get("products", [])

        if not os.path.exists(self.template_path):
            print(f"Error: Template not found at {self.template_path}")
            return None

        # Load Template
        wb = openpyxl.load_workbook(self.template_path)
        sheet = wb.active

        # Inject Headers
        sheet.cell(row=2, column=4, value=f"Costumer: {client_name}")
        sheet.cell(row=3, column=4, value=f"PO #: {project_po}")

        # The table headers are on Row 5. We will inject data starting at Row 20 to avoid 
        # overwriting the template's standard items, or we can clear them.
        # For this version, we will find the first empty row after row 5.
        start_row = 6
        while sheet.cell(row=start_row, column=4).value is not None:
            start_row += 1

        # Border styling for injected cells
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                             top=Side(style='thin'), bottom=Side(style='thin'))

        for item in items:
            # Map item data to columns
            # Column Mapping based on Row 5 headers:
            # C: Line Costing (Routing tag)
            # D: Item (Type)
            # E: Description
            # F: Color/Finish
            # G: Size (Dimensions)
            # H: Item code (SKU)
            # I: Brand
            # J: Supplier (Provider)
            # K: Qty
            
            # Skip if routing config prevents it
            routing_tag = item.get("routing_tag", "Standard")

            # Prepare values
            dims = item.get("dimensions", {})
            dim_str = "x".join(str(v) for v in dims.values()) if dims else ""

            row_data = {
                3: routing_tag,                   # C: Line Costing
                4: item.get("type", ""),          # D: Item
                5: item.get("description", ""),   # E: Description
                6: item.get("finish", ""),        # F: Color/Finish
                7: dim_str,                       # G: Size
                8: item.get("sku", item.get("id", "")), # H: Item code
                9: item.get("brand", ""),         # I: Brand
                10: item.get("provider", ""),     # J: Supplier
                11: item.get("qty", 1)            # K: Qty
            }

            for col_idx, value in row_data.items():
                cell = sheet.cell(row=start_row, column=col_idx, value=value)
                cell.border = thin_border
                
            start_row += 1

        output_path = os.path.join(self.output_dir, f"{client_name.replace(' ', '_')}_{project_po}_Materials_Cart.xlsx")
        wb.save(output_path)
        print(f"✅ Excel generated at: {output_path}")
        return output_path
